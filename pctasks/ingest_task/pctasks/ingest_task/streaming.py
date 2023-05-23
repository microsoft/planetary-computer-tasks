import json
import logging
import os
import traceback
from typing import Any, Dict, List, Optional, Tuple

import azure.storage.queue

from pctasks.core.models.base import PCBaseModel
from pctasks.core.models.item import IngestErrorType, ItemIngestErrorRecord
from pctasks.ingest.constants import DB_CONNECTION_STRING_ENV_VAR
from pctasks.ingest_task.pgstac import PgSTAC
from pctasks.ingest_task.task import ingest_item
from pctasks.task.context import TaskContext
from pctasks.task.streaming import NoOutput, StreamingTaskMixin, StreamingTaskOptions
from pctasks.task.task import Task

logger = logging.getLogger(__name__)


class StreamingIngestMessage(PCBaseModel):
    data: Dict[str, Any]


class StreamingIngestItemsInput(PCBaseModel):
    streaming_options: StreamingTaskOptions


class StreamingIngestItemsTask(
    StreamingTaskMixin, Task[StreamingIngestItemsInput, NoOutput]
):
    _input_model = StreamingIngestItemsInput
    _output_model = NoOutput

    def get_required_environment_variables(self) -> List[str]:
        return [DB_CONNECTION_STRING_ENV_VAR]

    # Mypy doesn't like us using a more specific type for the input here.
    # I'm not sure what the solution is. You should only call this
    # method with the task type.
    def get_extra_options(  # type: ignore[override]
        self, input: StreamingIngestItemsInput, context: TaskContext
    ) -> Dict[str, Any]:
        from pctasks.ingest_task.task import PgSTAC

        conn_str = os.environ[DB_CONNECTION_STRING_ENV_VAR]
        pgstac = PgSTAC(conn_str)

        return {"pgstac": pgstac}

    def cleanup(self, extra_options: Dict[str, Any]) -> None:
        pgstac: Optional[PgSTAC] = extra_options.get("pgstac")
        if pgstac:
            pgstac.db.close()

    def process_message(  # type: ignore[override]
        self,
        message: azure.storage.queue.QueueMessage,
        input: StreamingIngestItemsInput,
        context: TaskContext,
        pgstac: PgSTAC,
    ) -> Tuple[Any, Any]:
        # What errors can occur here?
        # 1. This message might not be valid JSON.
        # 2. The pgstac ingest might fail.
        err = None
        try:
            item = json.loads(message.content)
        except json.JSONDecodeError:
            logger.exception("Error decoding message for ingest")
            err = ItemIngestErrorRecord(
                type=IngestErrorType.INVALID_DATA,
                input=message.content,
                run_id=context.run_id,
                attempt=message.dequeue_count,
                traceback=traceback.format_exc(),
            )
        else:
            logger.info(
                "Loading item collection=%s id=%s", item["collection"], item["id"]
            )
            # note: we rely on the collection ID being set, since
            # we're potentially ingesting multiple items.
            # if input.collection_id:
            #     item["collection"] = input.collection_id
            try:
                ingest_item(pgstac, item)
            except Exception:
                logger.exception("Error during ingest")
                err = ItemIngestErrorRecord(
                    type=IngestErrorType.ITEM_INGEST,
                    input=message.content,
                    run_id=context.run_id,
                    attempt=message.dequeue_count,
                    traceback=traceback.format_exc(),
                )

        return (item, err)

    def finalize_message(
        self,
        message: azure.storage.queue.QueueMessage,
        context: TaskContext,
        result: Tuple[List[Any], Any],
        extra_options: Dict[str, Any],
    ) -> None:
        pass
