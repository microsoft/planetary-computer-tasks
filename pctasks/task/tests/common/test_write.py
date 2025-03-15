from pctasks.core.models.task import CompletedTaskResult
from pctasks.dev.blob import temp_azurite_blob_storage
from pctasks.dev.test_utils import run_test_task
from pctasks.task.common.write import TASK_PATH, WriteInput, WriteOutput


def test_write_text() -> None:
    with temp_azurite_blob_storage() as storage:
        input = WriteInput(content="hello world", uri=storage.get_uri("test1.txt"))
        task_result = run_test_task(input.dict(), TASK_PATH)
        assert isinstance(task_result, CompletedTaskResult)
        output = WriteOutput.model_validate(task_result.output)
        content = storage.read_text(storage.get_path(output.uri))
        assert content == input.content


def test_write_json() -> None:
    with temp_azurite_blob_storage() as storage:
        input = WriteInput(
            content={"one": {"two": 2, "three": 3}, "four": 4},
            uri=storage.get_uri("test2.txt"),
        )
        task_result = run_test_task(input.dict(), TASK_PATH)
        assert isinstance(task_result, CompletedTaskResult)
        output = WriteOutput.model_validate(task_result.output)
        content = storage.read_json(storage.get_path(output.uri))
        assert content == input.content


def test_write_list() -> None:
    with temp_azurite_blob_storage() as storage:
        input = WriteInput(
            content=["hello", "world", 3, {"one": "two"}],
            uri=storage.get_uri("test3.txt"),
        )
        task_result = run_test_task(input.dict(), TASK_PATH)
        assert isinstance(task_result, CompletedTaskResult)
        output = WriteOutput.model_validate(task_result.output)
        content = storage.read_json(storage.get_path(output.uri))
        assert content == input.content
