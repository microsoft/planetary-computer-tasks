import logging
import os
import re
from base64 import b64encode
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import argo_workflows
from argo_workflows.api import workflow_service_api
from argo_workflows.exceptions import NotFoundException
from argo_workflows.model.capabilities import Capabilities
from argo_workflows.model.container import Container
from argo_workflows.model.env_var import EnvVar
from argo_workflows.model.io_argoproj_workflow_v1alpha1_template import (
    IoArgoprojWorkflowV1alpha1Template,
)
from argo_workflows.model.io_argoproj_workflow_v1alpha1_workflow import (
    IoArgoprojWorkflowV1alpha1Workflow,
)
from argo_workflows.model.io_argoproj_workflow_v1alpha1_workflow_create_request import (
    IoArgoprojWorkflowV1alpha1WorkflowCreateRequest,
)
from argo_workflows.model.io_argoproj_workflow_v1alpha1_workflow_spec import (
    IoArgoprojWorkflowV1alpha1WorkflowSpec,
)
from argo_workflows.model.io_argoproj_workflow_v1alpha1_workflow_terminate_request import (  # noqa: E501
    IoArgoprojWorkflowV1alpha1WorkflowTerminateRequest,
)
from argo_workflows.model.object_meta import ObjectMeta
from argo_workflows.model.security_context import SecurityContext
from argo_workflows.models import (
    Affinity,
    IoArgoprojWorkflowV1alpha1Metadata,
    NodeAffinity,
    NodeSelector,
    NodeSelectorRequirement,
    NodeSelectorTerm,
)
from azure.storage.blob import BlobSasPermissions, generate_blob_sas

from pctasks.core.constants import (
    AZURITE_HOST_ENV_VAR,
    AZURITE_PORT_ENV_VAR,
    AZURITE_STORAGE_ACCOUNT_ENV_VAR,
    COSMOSDB_EMULATOR_HOST_ENV_VAR,
)
from pctasks.core.models.run import TaskRunStatus
from pctasks.core.models.workflow import WorkflowSubmitMessage
from pctasks.core.storage.blob import BlobStorage, BlobUri, generate_key_for_sas
from pctasks.core.utils import map_opt
from pctasks.run.models import PreparedTaskSubmitMessage
from pctasks.run.secrets.local import LOCAL_ENV_SECRETS_PREFIX
from pctasks.run.settings import RunSettings, WorkflowExecutorConfig
from pctasks.run.utils import get_workflow_path

logger = logging.getLogger(__name__)

IMAGE_PULL_BACKOFF = "ImagePullBackOff"
ERR_IMAGE_PULL = "ErrImagePull"


def get_pull_policy(image: str) -> str:
    split_image = image.split(":")
    if len(split_image) > 1:
        if split_image[-1].lower().startswith("v") or split_image[-1][:1].isdigit():
            return "IfNotPresent"
    return "Always"


class ArgoClient:
    def __init__(self, host: str, token: str, namespace: str) -> None:
        self.host = host
        self.token = token
        self.configuration = argo_workflows.Configuration(
            host=host, api_key={"BearerToken": token}
        )
        api_client = argo_workflows.ApiClient(self.configuration)
        self.api_instance = workflow_service_api.WorkflowServiceApi(
            api_client=api_client
        )
        self.namespace = namespace

    def _get_affinity(self, run_settings: RunSettings) -> Optional[Affinity]:
        if run_settings.argo_node_group:
            return Affinity(
                node_affinity=NodeAffinity(
                    required_during_scheduling_ignored_during_execution=NodeSelector(
                        node_selector_terms=[
                            NodeSelectorTerm(
                                match_expressions=[
                                    NodeSelectorRequirement(
                                        key="node_group",
                                        operator="In",
                                        values=[run_settings.argo_node_group],
                                    )
                                ]
                            )
                        ]
                    )
                )
            )
        return None

    def _get_annotations_and_labels(
        self, run_settings: RunSettings
    ) -> Tuple[Dict, Dict]:
        annotations = {}
        labels = {}

        if run_settings.task_workload_identity_client_id:
            labels.update({"azure.workload.identity/use": "true"})

            annotations.update(
                {
                    "azure.workload.identity/client-id": (
                        run_settings.task_workload_identity_client_id
                    ),
                    "azure.workload.identity/tenant-id": (
                        run_settings.task_workload_identity_tenant_id
                    ),
                }
            )

        return annotations, labels

    def submit_workflow(
        self,
        submit_msg: WorkflowSubmitMessage,
        run_id: str,
        executor_config: WorkflowExecutorConfig,
        runner_image: str,
    ) -> Dict[str, Any]:
        b64encoded_config = b64encode(executor_config.to_yaml().encode("utf-8")).decode(
            "utf-8"
        )

        run_settings = executor_config.run_settings

        workflow_path = get_workflow_path(run_id)
        workflow_uri = BlobUri(
            f"blob://{run_settings.blob_account_name}/"
            f"{run_settings.task_io_blob_container}/"
            f"{workflow_path}"
        )

        task_io_storage = BlobStorage.from_account_key(
            f"blob://{workflow_uri.storage_account_name}/{workflow_uri.container_name}",
            account_key=run_settings.blob_account_key,
            account_url=run_settings.blob_account_url,
        )

        task_io_storage.write_text(
            workflow_path,
            submit_msg.to_yaml(),
        )

        credential_options = generate_key_for_sas(
            run_settings.blob_account_url, run_settings.blob_account_key
        )
        input_blob_sas_token = generate_blob_sas(
            account_name=run_settings.blob_account_name,
            container_name=run_settings.task_io_blob_container,
            blob_name=workflow_path,
            start=datetime.utcnow(),
            expiry=datetime.utcnow() + timedelta(hours=24 * 7),
            permission=BlobSasPermissions(read=True),
            **credential_options,
        )

        env: List[EnvVar] = []

        # Transfer some env vars from caller for dev environments

        for env_var in [
            AZURITE_HOST_ENV_VAR,
            AZURITE_PORT_ENV_VAR,
            AZURITE_STORAGE_ACCOUNT_ENV_VAR,
            COSMOSDB_EMULATOR_HOST_ENV_VAR,
        ]:
            if env_var in os.environ:
                env.append(EnvVar(name=env_var, value=os.environ[env_var]))

        if run_settings.task_workload_identity_client_id:
            env.append(
                EnvVar(
                    name="AZURE_CLIENT_ID",
                    value=run_settings.task_workload_identity_client_id,
                )
            )
            env.append(
                EnvVar(
                    name="AZURE_TENANT_ID",
                    value=run_settings.task_workload_identity_tenant_id,
                )
            )
            kwargs = {"service_account_name": run_settings.task_service_account_name}
        else:
            kwargs = {}

        if run_settings.applicationinsights_connection_string:
            env.append(
                EnvVar(
                    name="APPLICATIONINSIGHTS_CONNECTION_STRING",
                    value=run_settings.applicationinsights_connection_string,
                )
            )

        # Enable local secrets for development environment
        if run_settings.local_secrets:
            for env_var in [
                k for k in os.environ if k.startswith(LOCAL_ENV_SECRETS_PREFIX)
            ]:
                env.append(EnvVar(name=env_var, value=os.environ[env_var]))

        argo_wf_name = (
            "wkflw-"
            + re.sub("[^a-z0-9]", "-", submit_msg.workflow.id).strip("-")
            + "-"
            + run_id
        )

        annotations, labels = self._get_annotations_and_labels(run_settings)

        templates = [
            IoArgoprojWorkflowV1alpha1Template(
                name="run-workflow",
                metadata=IoArgoprojWorkflowV1alpha1Metadata(
                    annotations=annotations, labels=labels
                ),
                container=Container(
                    image=runner_image,
                    image_pull_policy=get_pull_policy(runner_image),
                    command=["pctasks"],
                    env=env,
                    security_context=SecurityContext(
                        # Enables tools like py-spy for debugging
                        capabilities=Capabilities(add=["SYS_PTRACE"])
                    ),
                    args=[
                        "-v",
                        "run",
                        "remote",
                        str(workflow_uri),
                        "--sas",
                        input_blob_sas_token,
                        "--settings",
                        b64encoded_config,
                    ],
                ),
            )
        ]

        affinity = self._get_affinity(run_settings)
        if affinity:
            kwargs["affinity"] = affinity

        manifest = IoArgoprojWorkflowV1alpha1Workflow(
            metadata=ObjectMeta(generate_name=f"{argo_wf_name}-"),
            spec=IoArgoprojWorkflowV1alpha1WorkflowSpec(
                entrypoint="run-workflow",
                templates=templates,
                **kwargs,
            ),
        )

        api_client = argo_workflows.ApiClient(self.configuration)
        api_instance = workflow_service_api.WorkflowServiceApi(api_client=api_client)
        logger.info(f"Submitting workflow {argo_wf_name} to Argo...")
        api_response = api_instance.create_workflow(
            namespace=self.namespace,
            body=IoArgoprojWorkflowV1alpha1WorkflowCreateRequest(workflow=manifest),
            _check_return_type=False,
        )
        return api_response.to_dict()

    def submit_task(
        self, prepared_task: PreparedTaskSubmitMessage, run_settings: RunSettings
    ) -> Dict[str, Any]:

        submit_msg = prepared_task.task_submit_message
        job_id = submit_msg.job_id
        task_id = submit_msg.definition.id
        run_msg = prepared_task.task_run_message
        task_input_blob_config = prepared_task.task_input_blob_config
        task_image = run_msg.config.image

        argo_wf_name = "task-" + re.sub(
            "[^a-z0-9]", "-", f"{job_id}--{task_id}".lower()
        ).strip("-")

        command_args = [
            "task",
            "run",
            task_input_blob_config.uri,
            "--sas-token",
            task_input_blob_config.sas_token,
        ]

        env: List[EnvVar] = []

        # Transfer some env vars from caller for dev environments

        for env_var in [
            AZURITE_HOST_ENV_VAR,
            AZURITE_PORT_ENV_VAR,
            AZURITE_STORAGE_ACCOUNT_ENV_VAR,
        ]:
            if env_var in os.environ:
                env.append(EnvVar(name=env_var, value=os.environ[env_var]))

        if run_settings.task_workload_identity_client_id:
            env.append(
                EnvVar(
                    name="AZURE_CLIENT_ID",
                    value=run_settings.task_workload_identity_client_id,
                )
            )
            env.append(
                EnvVar(
                    name="AZURE_TENANT_ID",
                    value=run_settings.task_workload_identity_tenant_id,
                )
            )
            kwargs = {"service_account_name": run_settings.task_service_account_name}
        else:
            kwargs = {}

        if run_settings.applicationinsights_connection_string:
            env.append(
                EnvVar(
                    name="APPLICATIONINSIGHTS_CONNECTION_STRING",
                    value=run_settings.applicationinsights_connection_string,
                )
            )

        templates = [
            IoArgoprojWorkflowV1alpha1Template(
                name="run-workflow",
                container=Container(
                    image=task_image,
                    image_pull_policy=get_pull_policy(task_image),
                    command=["pctasks"],
                    env=env,
                    args=command_args,
                ),
            )
        ]

        affinity = self._get_affinity(run_settings)
        if affinity:
            kwargs["affinity"] = affinity

        manifest = IoArgoprojWorkflowV1alpha1Workflow(
            metadata=ObjectMeta(generate_name=f"{argo_wf_name}-"),
            spec=IoArgoprojWorkflowV1alpha1WorkflowSpec(
                entrypoint="run-workflow", templates=templates, **kwargs
            ),
        )

        api_response = self.api_instance.create_workflow(
            namespace=self.namespace,
            body=IoArgoprojWorkflowV1alpha1WorkflowCreateRequest(workflow=manifest),
            _check_return_type=False,
        )

        final_wf_name: str = api_response["metadata"]["name"]
        return {"namespace": self.namespace, "name": final_wf_name}

    def get_task_status(
        self, namespace: str, argo_workflow_name: str
    ) -> Optional[Tuple[TaskRunStatus, Optional[str]]]:
        """Returns the status of a task.

        If the task isn't found, returns None.
        If the is errored, will try to return the error message in
        the second tuple element.
        If the job is completed but the task is still running, will
        consider the task failed.
        Otherwise, returns the status as the first tuple element.
        """
        try:
            argo_workflow = self.api_instance.get_workflow(
                namespace=namespace,
                name=argo_workflow_name,
                _check_return_type=False,
            )
        except NotFoundException:
            return None

        status: Dict[str, Any] = argo_workflow["status"]
        phase_opt: Optional[str] = status.get("phase")
        phase: str = map_opt(lambda p: p.lower(), phase_opt) or "pending"

        logger.debug(
            f"Polling task: namespace: '{namespace}', name: '{argo_workflow_name}'"
        )

        # https://github.com/argoproj/argo-workflows/blob/19eae92db339fa79eb91fb71a50d330a18b09bcf/pkg/apis/workflow/v1alpha1/workflow_phase.go#L15  # noqa: E501
        if phase == "failed" or phase == "error":
            return (TaskRunStatus.FAILED, status.get("message"))
        elif phase == "running":
            # Ensure that there's not an ImagePullBackoff error
            nodes: Optional[Dict[str, Dict[str, Any]]] = status.get("nodes")
            if nodes:
                for node in nodes.values():
                    if node["phase"] == "Pending":
                        node_message = node.get("message")
                        if node_message and (
                            IMAGE_PULL_BACKOFF in node_message
                            or ERR_IMAGE_PULL in node_message
                        ):
                            logger.error(
                                f"Task {argo_workflow_name} can't pull image: "
                                f"{node['message']}"
                            )
                            self.terminate_workflow(namespace, argo_workflow_name)
                            return (TaskRunStatus.FAILED, node["message"])

            return (TaskRunStatus.RUNNING, None)
        elif phase == "succeeded":
            return (TaskRunStatus.COMPLETED, None)
        elif phase == "pending":
            return (TaskRunStatus.PENDING, None)
        else:
            return (TaskRunStatus.SUBMITTED, None)

    def terminate_workflow(self, namespace: str, argo_workflow_name: str) -> None:
        self.api_instance.terminate_workflow(
            namespace=namespace,
            name=argo_workflow_name,
            body=IoArgoprojWorkflowV1alpha1WorkflowTerminateRequest(
                namespace=namespace,
                name=argo_workflow_name,
            ),
            _check_return_type=False,
        )
