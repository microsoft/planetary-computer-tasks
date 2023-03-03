from __future__ import annotations

import logging
import urllib.parse
from typing import Any, Dict, Union

import kubernetes.client
import kubernetes.config
from kubernetes.client import (
    ApiException,
    AppsV1Api,
    CustomObjectsApi,
    V1ConfigMap,
    V1Container,
    V1Deployment,
    V1DeploymentSpec,
    V1EnvVar,
    V1ObjectMeta,
    V1PodSpec,
    V1PodTemplateSpec,
)

from pctasks.core.models.task import TaskDefinition
from pctasks.run.models import PreparedTaskSubmitMessage
from pctasks.run.settings import RunSettings
from pctasks.task.constants import (
    TASKIO_CLIENT_ID_ENV_VAR,
    TASKIO_CLIENT_SECRET_ENV_VAR,
    TASKIO_TENANT_ID_ENV_VAR,
)

logger = logging.getLogger(__name__)


# def submit_workflow(workflow_submit_message: WorkflowSubmitMessage, namespace="tasks"):
def submit_task(
    prepared_task: PreparedTaskSubmitMessage,
    run_settings: RunSettings,
):
    """
    Submit a streaming workflow for execution with Kubernetes.

    Parameters
    ----------
    workflow_submit_message : WorkflowSubmitMessage
        The submit message for a workflow.
    namespace : str, optional
        The Kubernetes namespace for the deployment and KEDA scaler, by default
        "tasks". This must already exist.
    """

    # Streaming jobs require TaskIO service principal to be set
    if (
        not run_settings.streaming_taskio_sp_tenant_id
        or not run_settings.streaming_taskio_sp_client_id
        or not run_settings.streaming_taskio_sp_client_secret
    ):
        raise ValueError("Streaming jobs require TaskIO service principal to be set")
    taskio_tenant_id = run_settings.streaming_taskio_sp_tenant_id
    taskio_client_id = run_settings.streaming_taskio_sp_client_id
    taskio_client_secret = run_settings.streaming_taskio_sp_client_secret

    # Load config stuff
    kubernetes.config.load_config()
    apps_api = AppsV1Api()
    objs_api = CustomObjectsApi()

    # Build the stuff
    # XXX: encode the task ID in the name of the object
    # Make sure to escape properly. Kinda hard.
    input_uri = prepared_task.task_input_blob_config.uri
    task = prepared_task.task_submit_message.definition
    deployment = build_streaming_deployment(
        task, input_uri, taskio_tenant_id, taskio_client_id, taskio_client_secret
    )
    scaler = build_streaming_scaler(task)

    # Submit the stuff
    namespace = run_settings.streaming_task_namespace
    logger.info("Ensuring deployment %s", deployment.metadata.name)
    create_or_update(deployment, apps_api, namespace=namespace)
    logger.info("Ensuring KEDA scaler %s", scaler["metadata"]["name"])
    create_or_update(
        scaler,
        objs_api,
        namespace=namespace,
        group="keda.sh",
        version="v1alpha1",
        plural="scaledobjects",
    )


def get_name_prefix(task_definition: TaskDefinition) -> str:
    """
    Get the prefix for a task. Used for Kubernetes resources.

    This combines the names of the Storage Account and Storage Queue.

    Parameters
    ----------
    task_definition: TaskDefintion
        The pctasks TaskDefintion. This *must* follow the streaming
        setup, so it should have a `queue_url` argument.
    """
    args = task_definition.args
    # XXX: We should be able to statically verify queue_url is a property
    pr = urllib.parse.urlparse(args["queue_url"])
    account_name = pr.netloc.split(".")[0]
    queue_name = pr.path.lstrip("/")
    return f"{account_name}-{queue_name}"


def get_deployment_name(task_definition: TaskDefinition) -> str:
    """
    Get the Kubernetes Deployment name for a Task Definition.
    """
    # TODO: validate this gracefully
    # assert isinstance(definition, StreamingCreateItemsConfig)
    prefix = get_name_prefix(task_definition)
    return f"{prefix}-deployment"


def build_streaming_scaler(task_definition: TaskDefinition):
    """
    Build, but don't submit, the data for a KEDA ScaledObject.
    """
    args = task_definition.args
    pr = urllib.parse.urlparse(args["queue_url"])
    account_name = pr.netloc.split(".")[0]
    queue_name = pr.path.lstrip("/")

    scaler_data = {
        "apiVersion": "keda.sh/v1alpha1",
        "kind": "ScaledObject",
        "metadata": {"name": f"{account_name}-{queue_name}-scaler"},
        "spec": {
            "scaleTargetRef": {"name": get_deployment_name(task_definition)},
            "minReplicaCount": args["min_replica_count"],
            "maxReplicaCount": args["max_replica_count"],
            "pollingInterval": args["polling_interval"],
            "triggers": [
                {
                    "type": "azure-queue",
                    "authenticationRef": {"name": "queue-connection-string-auth"},
                    "metadata": {
                        "queueName": queue_name,
                        "queueLength": str(args["trigger_queue_length"]),
                        "accountName": account_name,
                    },
                }
            ],
        },
    }
    return scaler_data


def build_streaming_deployment(
    task_definition: TaskDefinition,
    input_uri: str,
    taskio_tenant_id: str,
    taskio_client_id: str,
    taskio_client_secret: str,
) -> V1Deployment:
    """
    Build, but do not submit, a Kubernetes Deployment for a streaming task.

    Parameters
    ----------
    task_definition : TaskDefinition
        The pctasks TaskDefinition. This should be a streaming-style task.
    input_uri: str
        The URI of the input arguments for this task. It will likely be a
        ``blob://`` style URI pointing to base64-encoded arguments.

    Returns
    -------
    deployment
        A Kubernetes V1Deployment object. This will have a single pod with a
        single container.
    """
    env = [
        V1EnvVar(name=k, value=v)
        for k, v in {
            TASKIO_TENANT_ID_ENV_VAR: taskio_tenant_id,
            TASKIO_CLIENT_ID_ENV_VAR: taskio_client_id,
            TASKIO_CLIENT_SECRET_ENV_VAR: taskio_client_secret,
        }.items()
    ]

    container = V1Container(
        name="run-workflow",
        image=task_definition.image,
        image_pull_policy="IfNotPresent",
        command=["pctasks"],
        args=["task", "run", input_uri],
        env=env,
    )
    common_labels = {"node_group": "pc-lowlatency"}

    pod_spec = V1PodSpec(
        service_account_name="default",
        containers=[container],
        node_selector=common_labels,
    )
    pod_template_spec = V1PodTemplateSpec(
        metadata=V1ObjectMeta(
            labels=common_labels,
        ),
        spec=pod_spec,
    )
    deployment_spec = V1DeploymentSpec(
        template=pod_template_spec,
        selector={"matchLabels": common_labels},
    )
    deployment = V1Deployment(
        metadata=V1ObjectMeta(
            name=get_deployment_name(task_definition),
            labels=common_labels,
        ),
        spec=deployment_spec,
    )
    return deployment


def create_or_update(
    object: Union[V1ConfigMap, V1Deployment, Dict[str, Any]], api: Any, **kwargs: Any
) -> None:
    """
    Create or update a Kubernetes object.
    """
    if isinstance(object, V1ConfigMap):
        try:
            api.create_namespaced_config_map(**kwargs, body=object)
        except ApiException as e:
            if e.status == 409 and e.reason == "Conflict":
                api.patch_namespaced_config_map(
                    name=object.metadata.name, body=object, **kwargs
                )
            else:
                raise

    elif isinstance(object, V1Deployment):
        try:
            api.create_namespaced_deployment(**kwargs, body=object)
        except ApiException as e:
            if e.status == 409 and e.reason == "Conflict":
                api.patch_namespaced_deployment(
                    name=object.metadata.name, body=object, **kwargs
                )
            else:
                raise
    elif isinstance(object, dict):
        try:
            api.create_namespaced_custom_object(body=object, **kwargs)
        except ApiException as e:
            if e.status == 409 and e.reason == "Conflict":
                api.patch_namespaced_custom_object(
                    name=object["metadata"]["name"], body=object, **kwargs
                )
            else:
                raise
    else:
        raise TypeError(f"Unsupported type: {type(object)}")


# def prepare_task(
#     task: TaskDefinition,
#     run_id: str,
#     job_id: str,
#     account_name: str = "pctasksteststaging",  # TODO: run settings
# ) -> str:
#     """
#     Prepare a task for remote execution.

#     Parameters
#     ----------
#     task : TaskDefinition
#         A Task Definition. Note that

#         - The `code` attribute should have a `src` that's in `blob://` format.
#     run_id, job_id : str
#         The IDs for the run and job that this task is part of.

#     Returns
#     -------
#     input_uri : str
#         The URI of the task's input data. For blob storage, this will be
#         like `blob://{account_name}/taskio/{run_id}/0/{task_id}/input`.
#         The contents at that blob will be base64-encoded JSON.
#     """
#     task_id = task.id

#     status_uri = f"blob://{account_name}/taskio/status/{run_id}/0/{task_id}/status"
#     output_uri = f"blob://{account_name}/taskio/run/{run_id}/0/{task_id}/output"
#     log_uri = f"blob://{account_name}/taskio/status/{run_id}/0/{task_id}/task-log.txt"
#     input_uri = f"blob://{account_name}/taskio/run/{run_id}/{job_id}/0/{task_id}/input"

#     taskio = {
#         "args": task.args,
#         "config": {
#             "image": task.image,
#             "run_id": run_id,
#             "job_id": job_id,
#             "partition_id": "0",
#             "task_id": task.id,
#             "task": task.task,
#             "status_blob_config": {
#                 "account_url": f"https://{account_name}.blob.core.windows.net/",
#                 "uri": status_uri,
#             },
#             "output_blob_config": {
#                 "account_url": f"https://{account_name}.blob.core.windows.net/",
#                 "uri": output_uri,
#             },
#             "log_blob_config": {
#                 "account_url": f"https://{account_name}.blob.core.windows.net/",
#                 "uri": log_uri,
#             },
#         },
#     }

#     if task.code:
#         # XXX: the account_name stuff here isn't right. Already in the src maybe.
#         taskio["config"]["code_src_blob_config"] = {
#             "account_url": f"https://{account_name}.blob.core.windows.net/",
#             "uri": task.code.src,
#         }

#     credential = azure.identity.DefaultAzureCredential()
#     cc = azure.storage.blob.ContainerClient(
#         f"https://{account_name}.blob.core.windows.net", "taskio", credential=credential
#     )

#     _, path = input_uri.split("/taskio/", 1)

#     logger.info("Uploading task input to %s", input_uri)
#     with cc.get_blob_client(path) as bc:
#         data = base64.b64encode(json.dumps(taskio).encode())
#         bc.upload_blob(data, overwrite=True)

#     return input_uri
