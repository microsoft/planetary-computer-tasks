import os
import pathlib

import pytest

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
from pctasks.core.storage.blob import BlobStorage
from pctasks.dev.blob import AZURITE_ACCOUNT_KEY, AZURITE_HOST_ENV_VAR
from pctasks.dev.test_utils import assert_workflow_is_successful

HERE = pathlib.Path(__file__).parent


@pytest.fixture
def code_container():
    """Fixture providing the account URL and cleaning up test code."""
    hostname = os.getenv(AZURITE_HOST_ENV_VAR, "localhost")
    account_url = f"http://{hostname}:10000/devstoreaccount1"
    yield account_url


def test_client_submit(code_container: str):
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

    storage = BlobStorage.from_account_key(
        "blob://devstoreaccount1/code", AZURITE_ACCOUNT_KEY, code_container
    )
    path = storage.get_path(task.code.src)
    assert storage.file_exists(path)
