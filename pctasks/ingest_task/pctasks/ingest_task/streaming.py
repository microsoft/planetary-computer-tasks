import json
import logging
from typing import Any, Dict

import azure.storage.queue

from pctasks.core.models.base import PCBaseModel
from pctasks.ingest_task.pgstac import PgSTAC
from pctasks.task.context import TaskContext
from pctasks.task.task import Task
from pctasks.task.streaming import NoOutput, StreamingTaskMixin, StreamingTaskOptions
from pctasks.task.task import Task

logger = logging.getLogger(__name__)


class StreamingIngestItemsInput(PCBaseModel):
    streaming_options: StreamingTaskOptions


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

    def process_message(
        self,
        message: azure.storage.queue.QueueMessage,
        input: StreamingIngestItemsInput,
        context: TaskContext,
        pgstac: PgSTAC,
    ) -> None:
        from pctasks.ingest_task.task import ingest_item

        message = json.loads(message.content)
        item = message["data"]["item"]

        logger.info("Loading item collection=%s id=%s", item["collection"], item["id"])
        # note: we rely on the collection ID being set, since
        # we're potentially ingesting multiple items.
        # if input.collection_id:
        #     item["collection"] = input.collection_id
        ingest_item(pgstac, item)  # this hangs, at least on bad data.
