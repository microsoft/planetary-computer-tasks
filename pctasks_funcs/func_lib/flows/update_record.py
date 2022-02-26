import logging
from typing import Optional, Union

import azure.durable_functions as df
from azure.durable_functions.models.Task import TaskBase
from func_lib.activities import call_activity, parse_activity_exception

from pctasks.core.logging import RunLogger
from pctasks.core.models.base import RunRecordId
from pctasks.core.models.record import WorkflowRunStatus
from pctasks.execute.constants import ActivityNames
from pctasks.execute.models import (
    CreateJobRunRecordUpdate,
    CreateTaskRunRecordUpdate,
    CreateWorkflowRunGroupRecordUpdate,
    CreateWorkflowRunRecordUpdate,
    JobRunRecordUpdate,
    TaskRunRecordUpdate,
    UpdateRecordMessage,
    UpdateRecordResult,
    WorkflowRunGroupRecordUpdate,
    WorkflowRunRecordUpdate,
)

logger = logging.getLogger(__name__)


class UpdateRecordOrchFlow:
    def __init__(
        self,
        context: df.DurableOrchestrationContext,
        event_logger: RunLogger,
        run_record_id: RunRecordId,
    ) -> None:
        self.context = context
        self.event_logger = event_logger
        self.run_record_id = run_record_id

    def create_task(
        self,
        update: Union[
            CreateWorkflowRunGroupRecordUpdate,
            WorkflowRunGroupRecordUpdate,
            CreateWorkflowRunRecordUpdate,
            WorkflowRunRecordUpdate,
            CreateJobRunRecordUpdate,
            JobRunRecordUpdate,
            CreateTaskRunRecordUpdate,
            TaskRunRecordUpdate,
        ],
    ) -> TaskBase:
        return call_activity(
            self.context,
            name=ActivityNames.UPDATE_RECORD,
            msg=UpdateRecordMessage(
                update=update,
            ),
            run_record_id=self.run_record_id,
        )

    def handle_result(
        self, result: str, run_record_id: Optional[RunRecordId] = None
    ) -> UpdateRecordResult:
        create_record_result = UpdateRecordResult.parse_raw(result)
        if not self.context.is_replaying:
            if create_record_result.error:
                msg = (
                    "Failed to create or update run record. "
                    f"{create_record_result.error}"
                )
                self.event_logger.log_event(
                    WorkflowRunStatus.FAILED, properties={"error": msg}
                )

            self.event_logger.info(
                "Created or updated run record"
                + ("" if not run_record_id else f" for {run_record_id}")
            )

        return create_record_result

    def handle_error(self, e: Exception) -> None:
        self.event_logger.log_event(
            WorkflowRunStatus.FAILED, properties={"error": parse_activity_exception(e)}
        )
        logger.exception(e)
