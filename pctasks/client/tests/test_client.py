import pathlib

from pctasks.client.client import PCTasksClient
from pctasks.client.settings import ClientSettings
from pctasks.core.constants import MICROSOFT_OWNER
from pctasks.core.models.config import CodeConfig
from pctasks.core.models.dataset import DatasetIdentifier
from pctasks.core.models.task import TaskConfig
from pctasks.core.models.workflow import (
    JobConfig,
    WorkflowConfig,
    WorkflowSubmitMessage,
)
from pctasks.dev.blob import get_azurite_code_storage
from pctasks.dev.test_utils import assert_workflow_is_successful

HERE = pathlib.Path(__file__).parent


def test_client_submit():
    settings = ClientSettings.get()

    code = HERE.joinpath("data-files", "mycode.py").absolute()
    workflow = WorkflowConfig(
        name="Test Workflow!",
        dataset=DatasetIdentifier(owner=MICROSOFT_OWNER, name="test-dataset"),
        jobs={
            "test-job": JobConfig(
                tasks=[
                    TaskConfig(
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

    submit_message = WorkflowSubmitMessage(
        workflow=workflow,
    )

    client = PCTasksClient(settings)
    submitted_message = client.submit_workflow(submit_message)

    assert_workflow_is_successful(submit_message.run_id)

    task = submitted_message.workflow.jobs["test-job"].tasks[0]
    assert task.code
    assert task.code.src.startswith("blob://devstoreaccount1/code/")
    assert task.code.src.endswith("/mycode.py")

    storage = get_azurite_code_storage()
    path = storage.get_path(task.code.src)
    assert storage.file_exists(path)


def test_upload_code_file() -> None:
    settings = ClientSettings.get()
    storage = get_azurite_code_storage()
    client = PCTasksClient(settings)

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
    settings = ClientSettings.get()
    storage = get_azurite_code_storage()
    client = PCTasksClient(settings)

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
