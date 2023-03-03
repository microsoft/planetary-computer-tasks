import pytest

import pctasks.core.models.task
import pctasks.run.workflow.kubernetes


@pytest.fixture
def task_definition():
    """A task defintion for a streaming workflow."""
    return pctasks.core.models.task.TaskDefinition(
        **{
            "id": "create-items",
            "image": "pccomponentstest.azurecr.io/pctasks-goes-glm-streaming:2023.2.16.7",
            "code": {"src": "blob://pctasksteststaging/code/test-tom/goes_glm.py"},
            "task": "pctasks.dataset.streaming:StreamingCreateItemsTask",
            "args": {
                "queue_url": "https://pclowlatency.queue.core.windows.net/goes-glm",
                "visibility_timeout": 30,
                "options": {"skip_validation": False},
                "cosmos_endpoint": "https://pclowlatencytesttom.documents.azure.com:443/",
                "db_name": "lowlatencydb",
                "container_name": "items",
                "create_items_function": "goes_glm:GoesGlmCollection.create_item",
                "min_replica_count": 0,
                "max_replica_count": 10,
                "polling_interval": 30,
                "trigger_queue_length": 100,
                "collection_id": "goes-glm",
            },
            "schema_version": "1.0.0",
        }
    )


def test_get_deployment_name(task_definition):
    result = pctasks.run.workflow.kubernetes.get_deployment_name(task_definition)
    assert result == "pclowlatency-goes-glm-deployment"


def test_build_streaming_deployment(task_definition):
    result = pctasks.run.workflow.kubernetes.build_streaming_deployment(
        task_definition,
        input_uri="blob://pctasksteststaging/input",
        taskio_tenant_id="test-tenant-id",
        taskio_client_id="test-client-id",
        taskio_client_secret="test-client-secret",
    )
    labels = {"node_group": "pc-lowlatency"}
    assert result.metadata.name == "pclowlatency-goes-glm-deployment"
    name = "pclowlatency-goes-glm"
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


def test_build_streaming_scaler(task_definition):
    result = pctasks.run.workflow.kubernetes.build_streaming_scaler(task_definition)
    assert result["metadata"]["name"] == "pclowlatency-goes-glm-scaler"
    assert (
        result["spec"]["scaleTargetRef"]["name"] == "pclowlatency-goes-glm-deployment"
    )
    assert result["spec"]["minReplicaCount"] == 0
    assert result["spec"]["maxReplicaCount"] == 10
    assert result["spec"]["pollingInterval"] == 30
    assert result["spec"]["triggers"][0]["metadata"]["queueName"] == "goes-glm"
    assert result["spec"]["triggers"][0]["metadata"]["queueLength"] == "100"
    assert result["spec"]["triggers"][0]["metadata"]["accountName"] == "pclowlatency"
