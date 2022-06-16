import os
from pathlib import Path

from pctasks.core.models.task import CompletedTaskResult
from pctasks.dev.blob import temp_azurite_blob_storage
from pctasks.dev.test_utils import run_test_task
from pctasks.task.common.list_files import TASK_PATH, ListFilesInput, ListFilesOutput

HERE = Path(__file__).parent
TEST_DIR = HERE / ".." / "data-files" / "test-files"


def test_list_files_local() -> None:
    input = ListFilesInput(src_uri=str(TEST_DIR))

    task_result = run_test_task(input.dict(), TASK_PATH)

    assert isinstance(task_result, CompletedTaskResult)

    output = ListFilesOutput.parse_obj(task_result.output)

    print(output.uris)

    expected = [
        str(Path(root, f).resolve())
        for root, _, files in os.walk(TEST_DIR)
        for f in files
    ]

    print(expected)

    assert output.uris == expected


def test_list_files_blob() -> None:

    with temp_azurite_blob_storage(test_files=TEST_DIR) as storage:
        expected = set([storage.get_uri(p) for p in storage.list_files()])
        input = ListFilesInput(src_uri=storage.get_uri())

        task_result = run_test_task(input.dict(), TASK_PATH)

        assert isinstance(task_result, CompletedTaskResult)

        output = ListFilesOutput.parse_obj(task_result.output)

        assert set(output.uris) == expected
