import json
import logging
import os
import traceback
from typing import Any, Dict, List, Optional, Tuple, TypedDict

import azure.storage.queue

from pctasks.core.cosmos.containers.process_item_errors import (
    ProcessItemErrorsContainer,
)
from pctasks.core.models.base import PCBaseModel
from pctasks.core.models.event import IngestErrorType, IngestItemErrorRecord
from pctasks.ingest.constants import DB_CONNECTION_STRING_ENV_VAR
from pctasks.ingest_task.pgstac import PgSTAC
from pctasks.ingest_task.task import ingest_item
from pctasks.task.context import TaskContext
from pctasks.task.streaming import (
    NoOutput,
    StreamingTaskInput,
    StreamingTaskMixin,
    StreamingTaskOptions,
)
from pctasks.task.task import Task

logger = logging.getLogger(__name__)


class StreamingIngestMessage(PCBaseModel):
    data: Dict[str, Any]


class StreamingIngestItemsInput(PCBaseModel):
    streaming_options: StreamingTaskOptions


class ExtraOptions(TypedDict):
    pgstac: PgSTAC
    process_item_errors_container: ProcessItemErrorsContainer[IngestItemErrorRecord]


class StreamingIngestItemsTask(
    StreamingTaskMixin, Task[StreamingIngestItemsInput, NoOutput]
):
    _input_model = StreamingIngestItemsInput
    _output_model = NoOutput

    def get_required_environment_variables(self) -> List[str]:
        return [DB_CONNECTION_STRING_ENV_VAR]

    def get_extra_options(
        self, input: StreamingTaskInput, context: TaskContext
    ) -> ExtraOptions:
        assert isinstance(input, StreamingIngestItemsInput)

        conn_str = os.environ[DB_CONNECTION_STRING_ENV_VAR]
        pgstac = PgSTAC(conn_str)
        process_item_errors_container = ProcessItemErrorsContainer(
            IngestItemErrorRecord
        )
        process_item_errors_container.__enter__()

        return {
            "pgstac": pgstac,
            "process_item_errors_container": process_item_errors_container,
        }

    def cleanup(self, extra_options: ExtraOptions) -> None:
        pgstac: Optional[PgSTAC] = extra_options["pgstac"]
        if pgstac:
            pgstac.db.close()
        extra_options["process_item_errors_container"].__exit__(None, None, None)

    def process_message(
        self,
        message: azure.storage.queue.QueueMessage,
        input: StreamingTaskInput,
        context: TaskContext,
        extra_options: ExtraOptions,
    ) -> Tuple[Optional[Dict[str, Any]], Any]:
        assert isinstance(input, StreamingIngestItemsInput)

        pgstac = extra_options["pgstac"]
        # What errors can occur here?
        # 1. This message might not be valid JSON.
        # 2. The pgstac ingest might fail.
        item = err = None
        error_id = f"{message.id}:{context.run_id}:{message.dequeue_count}"
        try:
            item = json.loads(message.content)
        except json.JSONDecodeError:
            logger.exception("Error decoding message for ingest")
            err = IngestItemErrorRecord(
                id=error_id,
                type=IngestErrorType.INVALID_DATA,
                input=message.content,
                run_id=context.run_id,
                attempt=message.dequeue_count or 1,
                traceback=traceback.format_exc(),
            )
        else:
            logger.info(
                "Loading item collection=%s id=%s", item["collection"], item["id"]
            )

            try:
                ingest_item(pgstac, item)
            except Exception:
                logger.exception("Error during ingest")
                err = IngestItemErrorRecord(
                    id=error_id,
                    type=IngestErrorType.ITEM_INGEST,
                    input=message.content,
                    run_id=context.run_id,
                    attempt=message.dequeue_count or 1,
                    traceback=traceback.format_exc(),
                )

        return (item, err)

    def finalize_message(
        self,
        message: azure.storage.queue.QueueMessage,
        context: TaskContext,
        result: Tuple[Dict[str, Any], Any],
        extra_options: ExtraOptions,
    ) -> None:
        _, err = result
        process_item_errors_container = extra_options["process_item_errors_container"]

        if err:
            logger.info(
                "Recording error %s to %s",
                err.get_id(),
                process_item_errors_container.name,
            )
            process_item_errors_container.put(err)
