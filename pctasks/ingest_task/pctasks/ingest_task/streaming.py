import json
import logging
from typing import Any, Dict

import azure.storage.queue

from pctasks.core.models.base import PCBaseModel
from pctasks.ingest_task.pgstac import PgSTAC
from pctasks.task.task import Task
from pctasks.task.context import Task, TaskContext
from pctasks.task.streaming import NoOutput, StreamingTaskMixin, StreamingTaskOptions

logger = logging.getLogger(__name__)


class StreamingIngestItemsInput(PCBaseModel):
    streaming_options: StreamingTaskOptions
    collection_id: str


class StreamingIngestItemsTask(
    StreamingTaskMixin, Task[StreamingIngestItemsInput, NoOutput]
):
    _input_model = StreamingIngestItemsInput
    _output_model = NoOutput

    def get_extra_options(
        self, input: StreamingIngestItemsInput, context: TaskContext
    ) -> Dict[str, Any]:
        from pctasks.ingest_task.task import PgSTAC

        return {"pgstac": PgSTAC.from_env()}

    # TODO: figure out a typesafe way to get these extra arguments in here.
    def process_message(  # type: ignore
        self,
        message: azure.storage.queue.QueueMessage,
        input: StreamingIngestItemsInput,
        context: TaskContext,
        pgstac: PgSTAC,
    ) -> None:
        from pctasks.ingest_task.task import ingest_item

        item = json.loads(message.content)
        logger.info("Loading item")
        if input.collection_id:
            item["collection"] = input.collection_id
        ingest_item(pgstac, item)
