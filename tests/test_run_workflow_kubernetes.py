"""
Integration test for the Kubernetes Workflow Runner.

These tests rely on the Kind cluster and the test process having
access to the Kubernetes API.
"""
import base64
import os

import kubernetes
import pytest

import pctasks.core.models.task
from pctasks.core.constants import (
    AZURITE_HOST_ENV_VAR,
    AZURITE_PORT_ENV_VAR,
    AZURITE_STORAGE_ACCOUNT_ENV_VAR,
)
from pctasks.core.cosmos.settings import CosmosDBSettings
from pctasks.core.models.config import BlobConfig
from pctasks.core.models.workflow import (
    JobDefinition,
    Workflow,
    WorkflowDefinition,
    WorkflowSubmitMessage,
)
from pctasks.dev.k8s import get_streaming_task_definition
from pctasks.run.models import (
    PreparedTaskData,
    PreparedTaskSubmitMessage,
    TaskSubmitMessage,
)
from pctasks.run.settings import RunSettings, WorkflowExecutorConfig
from pctasks.run.workflow.executor.streaming import StreamingWorkflowExecutor

TEST_NAMESPACE = "pctasks-test"


@pytest.fixture(scope="session")
def run_settings():
    """Run settings, using azurite for storage."""
    key = (
        "Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq"
        "/K1SZFPTOtr/KBHBeksoGMGw=="
    )

    host = os.environ.get(AZURITE_HOST_ENV_VAR, "localhost")
    blob_port = int(os.environ.get(AZURITE_PORT_ENV_VAR, "10000"))

    return RunSettings(
        notification_queue={
            "account_url": "queue://devstoreaccount1/notifications",
            "connection_string": "connstr",
            "queue_name": "notifications",
            "sas_token": "sas",
        },
        tables_account_url=f"http://{host}:10001",
        tables_account_name="devstoreaccount1",
        tables_account_key="devstoreaccount1",
        blob_account_url=f"http://{host}:{blob_port}",
        blob_account_name="devstoreaccount1",
        blob_account_key=key,
        keyvault_url="https://devstoreaccount1.vault.azure.net/",
        task_runner_type="local",
        workflow_runner_type="local",
        local_dev_endpoints_url="http://localhost:7071",
        streaming_taskio_sp_client_id="test-client-id",
        streaming_taskio_sp_client_secret="test-client-secret",
        streaming_taskio_sp_tenant_id="test-tenant-id",
        streaming_task_namespace=TEST_NAMESPACE,
        local_secrets=True,
    )


@pytest.fixture(scope="session")
def namespace():
    """
    Setup the namespace for Kubernetes & KEDA Tests.

    This creates

    - A namespace called `pctasks-test`
    - A Kubernetes secret with the Account Key for an azurite storage queue
    - A KEDA TriggerAuthentication object

    The fixture is scoped to the session. The namespace is deleted as the
    session closes.
    """
    from kubernetes import client, config

    config.load_config()

    v1 = client.CoreV1Api()
    objects = client.CustomObjectsApi()
    ns = client.V1Namespace(metadata=client.V1ObjectMeta(name=TEST_NAMESPACE))
    try:
        v1.create_namespace(ns)
    except kubernetes.client.rest.ApiException as e:
        if e.status != 409:
            raise RuntimeError(
                "Namespace pctasks-test already exists. Manually delete the "
                "namespace to run this test."
            ) from e

    connstr = base64.b64encode(
        (
            "DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;"
            "AccountKey="
            "Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq"
            "/K1SZFPTOtr/KBHBeksoGMGw==;"
            "BlobEndpoint=http://127.0.0.1:10000/devstoreaccount1;"
            "QueueEndpoint=http://127.0.0.1:10001/devstoreaccount1;"
            "TableEndpoint=http://127.0.0.1.10002/devstoreaccount1;"
        ).encode()
    ).decode()

    v1.create_namespaced_secret(
        namespace=ns.metadata.name,
        body=client.V1Secret(
            data={"ConnectionString": connstr},
            metadata=client.V1ObjectMeta(
                name="secrets-storage-queue-connection-string"
            ),
        ),
    )
    body = {
        "apiVersion": "keda.sh/v1alpha1",
        "kind": "TriggerAuthentication",
        "metadata": {"name": "queue-connection-string-auth"},
        "spec": {
            "secretTargetRef": [
                {
                    "parameter": "connection",
                    "name": "secrets-storage-queue-connection-string",
                    "key": "ConnectionString",
                }
            ]
        },
    }
    objects.create_namespaced_custom_object(
        body=body,
        namespace=ns.metadata.name,
        group="keda.sh",
        version="v1alpha1",
        plural="triggerauthentications",
    )

    yield ns

    # this seems to return before the namespace is deleted
    v1.delete_namespace(name=ns.metadata.name)


def test_submit_task(namespace, run_settings):
    task_definition = get_streaming_task_definition()
    prepared_task = PreparedTaskSubmitMessage(
        task_submit_message=TaskSubmitMessage(
            dataset_id="test-dataset-id",
            run_id="test-run",
            job_id="job-id",
            partition_id="0",
            definition=task_definition,
        ),
        task_run_message=pctasks.core.models.task.TaskRunMessage(
            args={},
            config=pctasks.core.models.task.TaskRunConfig(
                image="image",
                run_id="test-run",
                job_id="job-id",
                partition_id="0",
                task_id="task-id",
                task=task_definition.task,
                status_blob_config=BlobConfig(
                    uri="blob://devstoreaccount1/taskio/status"
                ),
                output_blob_config=BlobConfig(
                    uri="blob://devstoreaccount1/taskio/output"
                ),
                log_blob_config=BlobConfig(uri="blob://devstoreaccount1/taskio/log"),
            ),
        ),
        task_input_blob_config=BlobConfig(uri="blob://devstoreaccount1/taskio/input"),
        task_data=PreparedTaskData(
            image="image",
            runner_info={},
        ),
    )
    # What do we want to assert here? What do we want to actually test?
    # We're only testing submit here. We don't care whether the task actually runs.
    pctasks.run.workflow.kubernetes.submit_task(prepared_task, run_settings)


@pytest.mark.parametrize(
    ["queue_url", "expected"],
    [
        (
            "http://127.0.0.1:10001/devstoreaccount1/test-queue",
            "devstoreaccount1-test-queue",
        ),
        (
            "http://azurite:10001/devstoreaccount1/test-queue",
            "devstoreaccount1-test-queue",
        ),
        ("https://goeseuwest.blob.core.windows.net/goes-glm", "goeseuwest-goes-glm"),
    ],
)
def test_get_name_prefix(queue_url, expected):
    result = pctasks.run.workflow.kubernetes.get_name_prefix(queue_url)
    assert result == expected


# via kubernetes Python library
# https://github.com/kubernetes-client/python/issues/2024
@pytest.mark.filterwarnings("ignore:HTTPResponse.getheaders:DeprecationWarning")
def test_execute_workflow(namespace, run_settings, monkeypatch):
    task_definition = get_streaming_task_definition()
    for k, v in {
        AZURITE_STORAGE_ACCOUNT_ENV_VAR: "devstoreaccount1",
        AZURITE_HOST_ENV_VAR: "127.0.0.1",
        AZURITE_PORT_ENV_VAR: "10000",
    }.items():
        if k not in os.environ:
            monkeypatch.setenv(k, v)

    settings = WorkflowExecutorConfig(
        run_settings=run_settings,
        cosmosdb_settings=CosmosDBSettings(),
    )
    executor = StreamingWorkflowExecutor(settings)
    definition = WorkflowDefinition(
        workflow_id="test",
        name="test",
        dataset_id="test",
        jobs={"test": JobDefinition(tasks=[task_definition])},
        is_streaming=True,
    )
    message = WorkflowSubmitMessage(
        run_id="test", workflow=Workflow(id="test", definition=definition)
    )

    # Here's the test.
    executor.execute_workflow(message)
