import os
from pathlib import Path

from pctasks.core.models.task import CompletedTaskResult
from pctasks.dev.blob import temp_azurite_blob_storage
from pctasks.dev.test_utils import run_test_task
from pctasks.task.common.list_prefixes import (
    TASK_PATH,
    ListPrefixesInput,
    ListPrefixesOutput,
)

HERE = Path(__file__).parent
TEST_DIR = HERE / ".." / "data-files" / "test-files"


def test_list_prefixes_local() -> None:
    input = ListPrefixesInput(src_uri=str(TEST_DIR), depth=1)

    task_result = run_test_task(input.dict(), TASK_PATH)

    assert isinstance(task_result, CompletedTaskResult)

    output = ListPrefixesOutput.parse_obj(task_result.output)

    print(output.uris)

    expected = [
        str((TEST_DIR / x).resolve())
        for x in os.listdir(TEST_DIR)
        if (TEST_DIR / x).is_dir()
    ]

    print(expected)

    assert set(output.uris) == set(expected)


def test_list_files_blob() -> None:

    with temp_azurite_blob_storage(test_files=TEST_DIR) as storage:
        expected = set([storage.get_uri(p) for p in storage.list_files()])
        input = ListPrefixesInput(src_uri=storage.get_uri(), depth=1)

        task_result = run_test_task(input.dict(), TASK_PATH)

        assert isinstance(task_result, CompletedTaskResult)

        output = ListPrefixesOutput.parse_obj(task_result.output)

        expected = [
            storage.get_uri(x) for x in os.listdir(TEST_DIR) if (TEST_DIR / x).is_dir()
        ]

        print(expected)

        assert set(output.uris) == set(expected)
