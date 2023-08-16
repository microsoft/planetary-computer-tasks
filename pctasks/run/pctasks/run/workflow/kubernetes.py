from __future__ import annotations

import logging
import urllib.parse
from typing import Any, Dict, Optional, Tuple, Union

import kubernetes.client
import kubernetes.config
from kubernetes.client import (
    ApiException,
    AppsV1Api,
    CustomObjectsApi,
    V1Affinity,
    V1ConfigMap,
    V1Container,
    V1Deployment,
    V1DeploymentSpec,
    V1EnvVar,
    V1NodeAffinity,
    V1NodeSelector,
    V1NodeSelectorRequirement,
    V1NodeSelectorTerm,
    V1ObjectMeta,
    V1PodSpec,
    V1PodTemplateSpec,
    V1PreferredSchedulingTerm,
    V1ResourceRequirements,
    V1Toleration,
)

from pctasks.core.models.task import TaskDefinition
from pctasks.run.models import PreparedTaskSubmitMessage
from pctasks.run.settings import RunSettings
from pctasks.task.constants import (
    TASKIO_CLIENT_ID_ENV_VAR,
    TASKIO_CLIENT_SECRET_ENV_VAR,
    TASKIO_TENANT_ID_ENV_VAR,
)
from pctasks.task.streaming import Resources

logger = logging.getLogger(__name__)
# This must match the TriggerAuthentication in
# deploy/helm/keda-trigger-authentication.yaml
KEDA_QUEUE_CONNECTION_STRING_AUTH_NAME = "queue-connection-string-auth"


def submit_task(
    prepared_task: PreparedTaskSubmitMessage,
    run_settings: RunSettings,
) -> None:
    """
    Submit a streaming workflow for execution with Kubernetes.

    This will typically run in an Argo Workflow-managed pod, which
    has been configured with all of the relevant run settings.

    Parameters
    ----------
    workflow_submit_message : WorkflowSubmitMessage
        The submit message for a workflow.
    namespace : str, optional
        The Kubernetes namespace for the deployment and KEDA scaler, by default
        "tasks". This must already exist.
    """

    # Streaming jobs require TaskIO service principal to be set
    if all(
        x is None
        for x in [
            run_settings.streaming_taskio_sp_tenant_id,
            run_settings.streaming_taskio_sp_client_id,
            run_settings.streaming_taskio_sp_client_secret,
        ]
    ):
        raise ValueError("Streaming jobs require TaskIO service principal to be set")

    # The previous check isn't sufficient for mypy to know these are set
    assert run_settings.streaming_taskio_sp_tenant_id is not None
    assert run_settings.streaming_taskio_sp_client_id is not None
    assert run_settings.streaming_taskio_sp_client_secret is not None

    # Load config stuff
    kubernetes.config.load_config()
    apps_api = AppsV1Api()
    objs_api = CustomObjectsApi()

    # Build the stuff
    input_uri = prepared_task.task_input_blob_config.uri
    task = prepared_task.task_submit_message.definition
    deployment = build_streaming_deployment(
        task,
        input_uri,
        run_settings.streaming_taskio_sp_tenant_id,
        run_settings.streaming_taskio_sp_client_id,
        run_settings.streaming_taskio_sp_client_secret,
        run_settings.streaming_task_node_group,
    )
    scaler = build_streaming_scaler(task)

    # Submit the stuff
    namespace = run_settings.streaming_task_namespace
    logger.info("Ensuring deployment %s", deployment.metadata.name)
    create_or_update(deployment, apps_api, namespace=namespace)
    logger.info("Ensuring KEDA scaler %s", scaler["metadata"]["name"])
    # TODO: We should verify that there's only one scaledobject per queue.
    # We don't want to accidentally have two things processing the same queue.
    # This should really be done at workflow submission time.
    create_or_update(
        scaler,
        objs_api,
        namespace=namespace,
        group="keda.sh",
        version="v1alpha1",
        plural="scaledobjects",
    )


def get_queue_parts(queue_url: str) -> Tuple[str, str]:
    pr = urllib.parse.urlparse(queue_url)
    if pr.netloc in ("127.0.0.1:10001", "azurite:10001"):
        # azurite
        account_name, queue_name = pr.path.lstrip("/").split("/")
    else:
        account_name = pr.netloc.split(".")[0]
        queue_name = pr.path.lstrip("/")
    return account_name, queue_name


def get_name_prefix(queue_url: str) -> str:
    """
    Get the prefix for a task. Used for Kubernetes resources.

    This combines the names of the Storage Account and Storage Queue.

    Parameters
    ----------
    queue_url : str
    """
    account_name, queue_name = get_queue_parts(queue_url)
    # mostly for azurite
    account_name = account_name.replace(":", ".").replace("/", ".")
    queue_name = queue_name.replace(":", ".").replace("/", ".")
    return f"{account_name}-{queue_name}"


def get_deployment_name(task_definition: TaskDefinition) -> str:
    """
    Get the Kubernetes Deployment name for a Task Definition.
    """
    # TODO: validate this gracefully
    prefix = get_name_prefix(task_definition.args["streaming_options"]["queue_url"])
    return f"{prefix}-deployment"


def build_streaming_scaler(task_definition: TaskDefinition) -> dict[str, Any]:
    """
    Build, but don't submit, the data for a KEDA ScaledObject.
    """
    account_name, queue_name = get_queue_parts(
        task_definition.args["streaming_options"]["queue_url"]
    )
    prefix = get_name_prefix(task_definition.args["streaming_options"]["queue_url"])
    args = task_definition.args

    scaler_data = {
        "apiVersion": "keda.sh/v1alpha1",
        "kind": "ScaledObject",
        "metadata": {"name": f"{prefix}-scaler"},
        "spec": {
            "scaleTargetRef": {"name": get_deployment_name(task_definition)},
            "minReplicaCount": args["streaming_options"]["min_replica_count"],
            "maxReplicaCount": args["streaming_options"]["max_replica_count"],
            "pollingInterval": args["streaming_options"]["polling_interval"],
            "triggers": [
                {
                    "type": "azure-queue",
                    "authenticationRef": {
                        "name": KEDA_QUEUE_CONNECTION_STRING_AUTH_NAME
                    },
                    "metadata": {
                        "queueName": queue_name,
                        "queueLength": str(
                            args["streaming_options"]["trigger_queue_length"]
                        ),
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
    node_group: Optional[str] = None,
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

    # This is really just used for setting the azurite env vars
    # in testing. Need to set that *before* the container starts.
    for k, v in task_definition.args.get("extra_env", {}).items():
        env.append(V1EnvVar(name=k, value=str(v)))

    resources = build_resources(
        Resources.parse_obj(task_definition.args["streaming_options"]["resources"])
    )

    container = V1Container(
        name="run-workflow",
        image=task_definition.image,
        image_pull_policy="Always",
        command=["pctasks"],
        args=["task", "run", input_uri],
        env=env,
        resources=resources,
    )

    queue_name = get_name_prefix(task_definition.args["streaming_options"]["queue_url"])

    common_labels = {
        "planetarycomputer.microsoft.com/queue_url": queue_name,
        "planetarycomputer.microsoft.com/task_type": "streaming",
    }
    if node_group:
        common_labels["node_group"] = node_group

    allow_spot_instances = task_definition.args["streaming_options"].get(
        "allow_spot_instances", False
    )
    node_selector = {"node_group": node_group} if node_group else None
    tolerations = []
    if node_group:
        logger.info("Adding node_affinity=%s", node_group)
        affinity = V1Affinity(
            node_affinity=V1NodeAffinity(
                required_during_scheduling_ignored_during_execution=V1NodeSelector(
                    node_selector_terms=[
                        V1NodeSelectorTerm(
                            match_expressions=[
                                V1NodeSelectorRequirement(
                                    key="node_group", operator="In", values=[node_group]
                                )
                            ]
                        )
                    ]
                )
            )
        )

        if allow_spot_instances:
            # add a preference for spot instances, if that's allowed
            logger.info("Adding spot preference")
            affinity.node_affinity.preferred_during_scheduling_ignored_during_execution = [  # noqa: E501
                V1PreferredSchedulingTerm(
                    weight=1,
                    preference=V1NodeSelectorTerm(
                        match_expressions=[
                            V1NodeSelectorRequirement(
                                key="kubernetes.azure.com/scalesetpriority",
                                operator="In",
                                values=["spot"],
                            )
                        ]
                    ),
                )
            ]
    else:
        affinity = None

    if allow_spot_instances:
        logger.info("Adding spot toleration")
        tolerations.append(
            V1Toleration(
                key="kubernetes.azure.com/scalesetpriority",
                operator="Equal",
                value="spot",
                effect="NoSchedule",
            )
        )

    pod_spec = V1PodSpec(
        service_account_name="default",
        containers=[container],
        node_selector=node_selector,
        tolerations=tolerations,
        affinity=affinity,
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


def build_resources(resources: Resources) -> V1ResourceRequirements:
    return V1ResourceRequirements(
        limits={
            "cpu": resources.limits.cpu,
            "memory": resources.limits.memory,
        },
        requests={
            "cpu": resources.requests.cpu,
            "memory": resources.requests.memory,
        },
    )


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
