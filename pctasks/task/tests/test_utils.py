import textwrap

from numpy import isin

from pctasks.core.models.config import BlobConfig
from pctasks.core.models.task import CompletedTaskResult
from pctasks.core.storage.blob import BlobStorage
from pctasks.dataset.chunks.task import create_chunks_task
from pctasks.dev.blob import temp_azurite_blob_storage
from pctasks.dev.test_utils import run_test_task
from pctasks.task.utils import get_task_path


class TestTaskHolder:
    task = create_chunks_task


def test_get_object_path_in_package():
    task_path = get_task_path(create_chunks_task, "create_chunks_task")
    assert task_path == "pctasks.dataset.chunks.task:create_chunks_task"


def test_get_task_path_in_class():
    task_path = get_task_path(
        TestTaskHolder.task, "TestTaskHolder.task", module=TestTaskHolder.__module__
    )
    assert task_path == "tests.test_utils:TestTaskHolder.task"


def test_ensure_code():
    src = textwrap.dedent(
        """\
    from pctasks.task.task import Task

    class InputModel:
        def parse_obj(data):
            return None

    class OutputModel:
        def dict(self):
            return {"result": 1}

    class MyTask(Task):
        _input_model = InputModel
        _output_model = OutputModel

        def __init__(self):
            self.call_count = 0

        def run(self, input, context):
            return OutputModel()
    """
    )

    with temp_azurite_blob_storage() as storage:
        assert isinstance(storage, BlobStorage)
        task_run_config_options = {
            "code_blob_config": BlobConfig(
                account_url=storage.account_url,
                uri=storage.get_uri("mymodule.py"),
                sas_token=storage.sas_token,
            )
        }
        storage.upload_bytes(src.encode(), "mymodule.py")

        # The test
        result = run_test_task(
            {}, "mymodule:MyTask", task_run_config_options=task_run_config_options
        )
        assert result.output == {"result": 1}
