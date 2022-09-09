from functools import reduce
import logging
from typing import Any, Dict, List, Optional

from pctasks.core.models.base import PCBaseModel
from pctasks.core.utils.summary import ObjectSummary, SummarySettings
from pctasks.task.context import TaskContext
from pctasks.task.task import Task
from pctasks.task.utils import get_task_path


logger = logging.getLogger(__name__)


class SummarizeMapInput(PCBaseModel):
    uris: List[str]
    include_keys: Optional[List[str]] = None
    is_ndjson: bool = False
    summary_settings: SummarySettings = SummarySettings()


class SummarizeOutput(PCBaseModel):
    summary: ObjectSummary


class SummarizeReduceInput(PCBaseModel):
    summaries: List[ObjectSummary]
    summary_settings: SummarySettings = SummarySettings()


class SummarizeMapTask(Task[SummarizeMapInput, SummarizeOutput]):
    _input_model = SummarizeMapInput
    _output_model = SummarizeOutput

    def run(self, input: SummarizeMapInput, context: TaskContext) -> SummarizeOutput:
        summary: Optional[ObjectSummary] = None
        total = len(input.uris)
        for i, uri in enumerate(input.uris):
            logger.info(f"Summarizing {uri} ({i+1} of {total})...")
            storage, path = context.storage_factory.get_storage_for_file(uri)
            objects: List[Dict[str, Any]] = []
            if not input.is_ndjson:
                objects.append(storage.read_json(path))
            else:
                objects.extend(storage.read_ndjson(path))

            this_summary = ObjectSummary.summarize(
                *objects,
                include_keys=input.include_keys,
                settings=input.summary_settings,
            )
            if summary is None:
                summary = this_summary
            else:
                summary = summary.merge(this_summary, settings=input.summary_settings)

        if not summary:
            raise Exception(f"No summary generated from input (total uris: {total})")

        return SummarizeOutput(summary=summary)


class SummarizeReduceTask(Task[SummarizeReduceInput, SummarizeOutput]):
    _input_model = SummarizeReduceInput
    _output_model = SummarizeOutput

    def run(self, input: SummarizeReduceInput, context: TaskContext) -> SummarizeOutput:
        summary = reduce(
            lambda a, b: a.merge(b, settings=input.summary_settings), input.summaries
        )
        return SummarizeOutput(summary=summary)


map_task = SummarizeMapTask()
reduce_task = SummarizeReduceTask()
MAP_TASK_PATH = get_task_path(map_task, "map_task")
REDUCE_TASK_PATH = get_task_path(reduce_task, "reduce_task")
