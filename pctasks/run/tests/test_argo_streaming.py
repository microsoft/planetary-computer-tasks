import pytest

from pctasks.core.models.config import BlobConfig
from pctasks.core.models.task import TaskRunConfig, TaskRunMessage
from pctasks.run.argo.client import ArgoClient
from pctasks.run.models import (
    PreparedTaskData,
    PreparedTaskSubmitMessage,
    TaskSubmitMessage,
)
from pctasks.task.streaming import StreamingCreateItemsConfig, StreamingCreateItemsInput


@pytest.fixture
def message():
    run_id = "test-run"
    job_id = "test-job"
    partition_id = "test-partition"
    image = "test-image:latest"

    task_config = StreamingCreateItemsConfig.create(
        task_id="create-items",
        queue_url="https://pclowlatency.queue.core.windows.net/goes-glm",
        visibility_timeout=30,
        create_items_function="goes_glm:GoesGlmCollection.create_item",
        image="na",
    )

    return PreparedTaskSubmitMessage(
        task_submit_message=TaskSubmitMessage(
            dataset_id="test-dataset",
            run_id="test-run",
            job_id="test-job",
            partition_id="0",
            definition=task_config,
        ),
        task_run_message=TaskRunMessage(
            args={},
            config=TaskRunConfig(
                image=image,
                run_id=run_id,
                job_id=job_id,
                partition_id=partition_id,
                task_id=task_config.id,
                task=task_config.task,
                status_blob_config=BlobConfig(uri="test", sas_token="test"),
                log_blob_config=BlobConfig(uri="test", sas_token="test"),
                output_blob_config=BlobConfig(uri="test", sas_token="test"),
            ),
        ),
        task_input_blob_config=BlobConfig(uri="test", sas_token="test"),
        task_data=PreparedTaskData(image=image, environment={}, runner_info={}),
    )


def test_get_deployment_name(message):
    client = ArgoClient("host", "token", namespace="pctasks")
    result = client._get_deployment_name(message)
    assert result == "pclowlatency-goes-glm-deployment"


def test_build_streaming_deployment(message):
    client = ArgoClient("host", "token", namespace="pctasks")
    result = client._build_streaming_deployment(
        "pctasks-task:latest", ["foo", "bar"], message
    )
    assert result.metadata.name == "pclowlatency-goes-glm-deployment"
    name = "pclowlatency-goes-glm"
    assert result.metadata.labels == {"app.kubernetes.io/name": name}
    assert result.spec.selector["matchLabels"] == {"app.kubernetes.io/name": name}
    assert result.spec.template.metadata.labels == {
        "app.kubernetes.io/name": name,
        "azure.workload.identity/use": "true",
    }
    assert result.spec.template.spec.service_account_name == "workload-identity-sa"
    assert result.spec.template.spec.containers[0].image == "pctasks-task:latest"
    assert result.spec.template.spec.containers[0].args == ["foo", "bar"]


def test_build_streaming_scaler(message):
    client = ArgoClient("host", "token", namespace="pctasks")
    result = client._build_streaming_scaler(message)
    assert result["metadata"]["name"] == "pclowlatency-goes-glm-scaler"
    assert (
        result["spec"]["scaleTargetRef"]["name"] == "pclowlatency-goes-glm-deployment"
    )
    assert result["spec"]["minReplicaCount"] == 0
    assert result["spec"]["maxReplicaCount"] == 100
    assert result["spec"]["pollingInterval"] == 30
    assert result["spec"]["triggers"][0]["metadata"]["queueName"] == "goes-glm"
    assert result["spec"]["triggers"][0]["metadata"]["queueLength"] == "100"
    assert result["spec"]["triggers"][0]["metadata"]["accountName"] == "pclowlatency"
