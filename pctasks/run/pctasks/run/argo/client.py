import os
import re
from base64 import b64encode
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import argo_workflows
from argo_workflows.api import workflow_service_api
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
from argo_workflows.model.object_meta import ObjectMeta
from azure.storage.blob import BlobSasPermissions, generate_blob_sas

from pctasks.core.constants import (
    AZURITE_HOST_ENV_VAR,
    AZURITE_PORT_ENV_VAR,
    AZURITE_STORAGE_ACCOUNT_ENV_VAR,
)
from pctasks.core.models.workflow import WorkflowSubmitMessage
from pctasks.core.storage.blob import BlobStorage, BlobUri
from pctasks.run.secrets.local import LOCAL_SECRETS_PREFIX
from pctasks.run.settings import RunSettings
from pctasks.run.utils import get_workflow_path
from pctasks.server.settings import ServerSettings


class ArgoClient:
    def __init__(self, host: str, token: str, namespace: str) -> None:
        self.host = host
        self.token = token
        self.configuration = argo_workflows.Configuration(
            host=host, api_key={"BearerToken": token}
        )
        self.namespace = namespace

    def submit_workflow(
        self,
        workflow: WorkflowSubmitMessage,
        run_settings: RunSettings,
        runner_image: Optional[str] = None,
    ) -> Dict[str, Any]:
        b64encoded_settings = b64encode(run_settings.to_yaml().encode("utf-8")).decode(
            "utf-8"
        )

        runner_image = runner_image or ServerSettings.get().runner_image

        workflow_path = get_workflow_path(workflow.run_id)
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
            workflow.to_yaml(),
        )

        input_blob_sas_token = generate_blob_sas(
            account_name=run_settings.blob_account_name,
            account_key=run_settings.blob_account_key,
            container_name=run_settings.task_io_blob_container,
            blob_name=workflow_path,
            start=datetime.now(),
            expiry=datetime.utcnow() + timedelta(hours=24 * 7),
            permission=BlobSasPermissions(read=True),
        )

        env: List[EnvVar] = []
        # Transfer some env vars from server

        for env_var in [
            AZURITE_HOST_ENV_VAR,
            AZURITE_PORT_ENV_VAR,
            AZURITE_STORAGE_ACCOUNT_ENV_VAR,
        ]:
            if env_var in os.environ:
                env.append(EnvVar(name=env_var, value=os.environ[env_var]))

        # Enable local secrets for development environment
        if run_settings.local_secrets:
            for env_var in [
                k for k in os.environ if k.startswith(LOCAL_SECRETS_PREFIX)
            ]:
                env.append(EnvVar(name=env_var, value=os.environ[env_var]))

        argo_wf_name = "pc-wf-" + re.sub(
            "[^a-z0-9]", "-", workflow.workflow.name.lower()
        ).strip("-")

        manifest = IoArgoprojWorkflowV1alpha1Workflow(
            metadata=ObjectMeta(generate_name=f"{argo_wf_name}-"),
            spec=IoArgoprojWorkflowV1alpha1WorkflowSpec(
                entrypoint="run-workflow",
                templates=[
                    IoArgoprojWorkflowV1alpha1Template(
                        name="run-workflow",
                        container=Container(
                            image=runner_image,
                            command=["pctasks"],
                            env=env,
                            args=[
                                "run",
                                "remote",
                                str(workflow_uri),
                                "--sas",
                                input_blob_sas_token,
                                "--settings",
                                b64encoded_settings,
                            ],
                        ),
                    )
                ],
            ),
        )
        api_client = argo_workflows.ApiClient(self.configuration)
        api_instance = workflow_service_api.WorkflowServiceApi(api_client=api_client)

        # TODO: Remove
        import ssl
        ssl._create_default_https_context = ssl._create_unverified_context

        api_response = api_instance.create_workflow(
            namespace=self.namespace,
            body=IoArgoprojWorkflowV1alpha1WorkflowCreateRequest(workflow=manifest),
            _check_return_type=False,
        )
        return api_response.to_dict()
