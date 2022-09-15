from pathlib import Path
from typing import List

from pctasks.core.models.task import CompletedTaskResult
from pctasks.core.utils.summary import KeySet
from pctasks.dev.blob import temp_azurite_blob_storage
from pctasks.dev.test_utils import run_test_task
from pctasks.task.common.list_files import TASK_PATH as LIST_FILES_TASK_PATH
from pctasks.task.common.list_files import ListFilesInput, ListFilesOutput
from pctasks.task.common.list_prefixes import TASK_PATH as LIST_PREFIXES_TASK_PATH
from pctasks.task.common.list_prefixes import ListPrefixesInput, ListPrefixesOutput
from pctasks.task.common.summarize import (
    MAP_TASK_PATH,
    REDUCE_TASK_PATH,
    SummarizeMapInput,
    SummarizeOutput,
    SummarizeReduceInput,
)

HERE = Path(__file__).parent
TEST_JSONS_DIR = HERE / ".." / "data-files/items/s1-rtc/2019/12/15/IW"
TEST_NDJSONS_DIR = HERE / ".." / "data-files/items/s1-rtc-ndjson"


def test_summarize_jsons() -> None:
    with temp_azurite_blob_storage(test_files=TEST_JSONS_DIR) as storage:

        prefix_input = ListPrefixesInput(src_uri=storage.get_uri(), depth=1)
        prefix_task_result = run_test_task(prefix_input.dict(), LIST_PREFIXES_TASK_PATH)
        assert isinstance(prefix_task_result, CompletedTaskResult)
        prefix_output = ListPrefixesOutput.parse_obj(prefix_task_result.output)

        map_outputs: List[SummarizeOutput] = []
        for prefix_uri in prefix_output.uris:
            list_files_input = ListFilesInput(src_uri=prefix_uri, extensions=[".json"])
            files_task_result = run_test_task(
                list_files_input.dict(), LIST_FILES_TASK_PATH
            )
            assert isinstance(files_task_result, CompletedTaskResult)
            files_output = ListFilesOutput.parse_obj(files_task_result.output)

            map_input = SummarizeMapInput(uris=files_output.uris)
            map_task_result = run_test_task(map_input.dict(), MAP_TASK_PATH)
            assert isinstance(map_task_result, CompletedTaskResult)
            map_output = SummarizeOutput.parse_obj(map_task_result.output)
            map_outputs.append(map_output)

        reduce_input = SummarizeReduceInput(summaries=[x.summary for x in map_outputs])
        reduce_task_result = run_test_task(reduce_input.dict(), REDUCE_TASK_PATH)
        assert isinstance(reduce_task_result, CompletedTaskResult)
        reduce_output = SummarizeOutput.parse_obj(reduce_task_result.output)
        summary = reduce_output.summary.dict()

        assert set(
            [
                v["value"]
                for v in summary["keys"]["properties"]["summary"]["keys"][
                    "sat:orbit_state"
                ]["values"]
            ]
        ) == set(["descending", "ascending"])

        assert summary["keys"]["assets"]["summary"]["key_sets"]["values"] == [
            KeySet(keys=set(["hv-rtc", "hh-rtc"]), count_with=4),
            KeySet(keys=set(["vv-rtc", "vh-rtc"]), count_with=4),
        ]
