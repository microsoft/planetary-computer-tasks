import pathlib

import pytest

from pctasks.client.client import PCTasksClient
from pctasks.core.models.config import CodeConfig
from pctasks.core.models.task import TaskDefinition
from pctasks.core.models.workflow import JobDefinition, WorkflowDefinition
from pctasks.dev.blob import get_azurite_code_storage
from pctasks.dev.test_utils import assert_workflow_is_successful

# from pctasks.dev.test_utils import assert_workflow_is_successful

HERE = pathlib.Path(__file__).parent


@pytest.mark.usefixtures("temp_cosmosdb_containers")
def test_client_submit():
    code = HERE.joinpath("data-files", "mycode.py").absolute()
    workflow = WorkflowDefinition(
        workflow_id="unittest-workflow-test_client_submit",
        name="Test Workflow!",
        dataset_id="test-dataset",
        jobs={
            "test-job": JobDefinition(
                tasks=[
                    TaskDefinition(
                        id="submit_unit_test",
                        image="pctasks-ingest:latest",
                        code=CodeConfig(src=str(code)),
                        task="mycode:MyMockTask",
                        args={"result_path": "/dev/null"},
                    )
                ],
            )
        },
    )

    client = PCTasksClient()
    submit_result = client.upsert_and_submit_workflow(workflow)

    assert_workflow_is_successful(submit_result.run_id, timeout_seconds=60)

    workflow_run = client.get_workflow_run(submit_result.run_id)
    assert workflow_run
    workflow_record = client.get_workflow(workflow_run.workflow_id)
    assert workflow_record
    workflow = workflow_record.workflow

    task = workflow.definition.jobs["test-job"].tasks[0]
    assert task.code
    assert task.code.src.startswith("blob://devstoreaccount1/code/")
    assert task.code.src.endswith("/mycode.py")

    storage = get_azurite_code_storage()
    path = storage.get_path(task.code.src)
    assert storage.file_exists(path)


def test_upload_code_file() -> None:
    storage = get_azurite_code_storage()
    client = PCTasksClient()

    code = pathlib.Path(__file__).absolute()
    result = client.upload_code(code)
    remote_path = storage.get_path(result.uri)

    try:
        assert storage.file_exists(remote_path)
        bytes = storage.read_bytes(remote_path)
        assert len(bytes) > 0
    finally:
        if storage.file_exists(remote_path):
            storage.delete_file(remote_path)


def test_upload_code_dir() -> None:
    storage = get_azurite_code_storage()
    client = PCTasksClient()

    code = HERE.absolute()
    result = client.upload_code(code)
    remote_path = storage.get_path(result.uri)

    try:
        assert storage.file_exists(remote_path)
        bytes = storage.read_bytes(remote_path)
        assert len(bytes) > 0
    finally:
        if storage.file_exists(remote_path):
            storage.delete_file(remote_path)
