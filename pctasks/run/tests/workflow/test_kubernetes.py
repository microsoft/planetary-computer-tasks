import pctasks.core.models.task
import pctasks.run.workflow.kubernetes
from pctasks.dev.k8s import get_streaming_task_definition


def test_get_deployment_name():
    task_definition = get_streaming_task_definition()
    result = pctasks.run.workflow.kubernetes.get_deployment_name(task_definition)
    assert result == "devstoreaccount1-test-deployment"


def test_build_streaming_deployment():
    task_definition = get_streaming_task_definition()
    result = pctasks.run.workflow.kubernetes.build_streaming_deployment(
        task_definition,
        input_uri="blob://pctasksteststaging/input",
        taskio_tenant_id="test-tenant-id",
        taskio_client_id="test-client-id",
        taskio_client_secret="test-client-secret",
    )
    labels = {
        "node_group": "pc-lowlatency",
        "planetarycomputer.microsoft.com/queue_url": "devstoreaccount1-test",
    }

    assert result.metadata.name == "devstoreaccount1-test-deployment"
    assert result.metadata.labels == labels
    assert result.spec.selector["matchLabels"] == labels
    assert result.spec.template.metadata.labels == labels
    assert result.spec.template.spec.service_account_name == "default"
    assert result.spec.template.spec.containers[0].image == task_definition.image
    assert result.spec.template.spec.containers[0].args == [
        "task",
        "run",
        "blob://pctasksteststaging/input",
    ]


def test_build_streaming_scaler():
    task_definition = get_streaming_task_definition()
    result = pctasks.run.workflow.kubernetes.build_streaming_scaler(task_definition)
    assert result["metadata"]["name"] == "devstoreaccount1-test-scaler"
    assert (
        result["spec"]["scaleTargetRef"]["name"] == "devstoreaccount1-test-deployment"
    )
    assert result["spec"]["minReplicaCount"] == 0
    assert result["spec"]["maxReplicaCount"] == 10
    assert result["spec"]["pollingInterval"] == 30
    assert result["spec"]["triggers"][0]["metadata"]["queueName"] == "test"
    assert result["spec"]["triggers"][0]["metadata"]["queueLength"] == "100"
    assert (
        result["spec"]["triggers"][0]["metadata"]["accountName"] == "devstoreaccount1"
    )


def test_get_deployment_name_azurite():
    task_definition = get_streaming_task_definition()
    task_definition.args["streaming_options"][
        "queue_url"
    ] = "http://localhost:10001/devstoreaccount1/test-queue-stream"
    result = pctasks.run.workflow.kubernetes.get_deployment_name(task_definition)
    assert result == "localhost.10001-devstoreaccount1.test-queue-stream-deployment"
