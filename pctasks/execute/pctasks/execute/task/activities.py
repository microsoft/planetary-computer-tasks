import json
import logging
import os
from typing import Any, Dict

from pctasks.core.logging import RunLogger
from pctasks.core.models.event import NotificationSubmitMessage
from pctasks.core.models.record import TaskRunStatus
from pctasks.core.models.task import (
    CompletedTaskResult,
    FailedTaskResult,
    TaskResultType,
    WaitTaskResult,
)
from pctasks.core.queues import QueueService
from pctasks.core.storage import get_storage_for_file
from pctasks.core.storage.blob import BlobStorage
from pctasks.execute.executor import get_executor
from pctasks.execute.models import (
    CreateJobRunRecordUpdate,
    CreateTaskRunRecordUpdate,
    CreateWorkflowRunGroupRecordUpdate,
    CreateWorkflowRunRecordUpdate,
    FailedSubmitResult,
    HandledTaskResult,
    HandleTaskResultMessage,
    JobRunRecordUpdate,
    NotificationSubmitResult,
    TaskPollMessage,
    TaskPollResult,
    TaskSubmitMessage,
    TaskSubmitResult,
    UpdateRecordMessage,
    UpdateRecordResult,
    WorkflowRunGroupRecordUpdate,
    WorkflowRunRecordUpdate,
)
from pctasks.execute.settings import ExecutorSettings
from pctasks.execute.task.submit import submit_task
from pctasks.submit.client import SubmitClient

logger = logging.getLogger(__name__)


def submit(msg: TaskSubmitMessage, event_logger: RunLogger) -> TaskSubmitResult:
    event_logger.log(msg.json(indent=2))
    settings = ExecutorSettings.get()
    try:
        return submit_task(
            msg,
            event_logger=event_logger,
            settings=settings,
        )
    except Exception as e:
        event_logger.error(f"Failed to submit task: {e}")
        return TaskSubmitResult(result=FailedSubmitResult(errors=[str(e)]))


def poll(msg: TaskPollMessage, event_logger: RunLogger) -> TaskPollResult:
    settings = ExecutorSettings.get()
    executor = get_executor(settings)
    try:
        result = executor.poll_task(
            msg.executor_id,
            previous_poll_count=msg.previous_poll_count,
            settings=settings,
        )
        logger.info(f"Polled task {msg.executor_id}: {result}")
        return result
    except Exception as e:
        if event_logger:
            event_logger.log_event(
                TaskRunStatus.FAILED, message=f"Failed to poll task: {e}"
            )
        error_lines = str(e).split("\n")

        return TaskPollResult(
            task_status=TaskRunStatus.FAILED,
            poll_errors=[f"Failed to poll task {json.dumps(msg.executor_id)}"]
            + error_lines,
        )


def handle_result(
    msg: HandleTaskResultMessage, event_logger: RunLogger
) -> HandledTaskResult:
    settings = ExecutorSettings.get()
    output_uri = msg.submit_result.output_uri
    output: Dict[str, Any] = {}

    event_logger.log_event(msg.task_result_type, message="Handling task result.")

    storage, path = get_storage_for_file(
        msg.log_uri,
        account_key=settings.blob_account_key,
        account_url=settings.blob_account_url,
    )
    log_uri_exists = storage.file_exists(path)
    log_uris = [msg.log_uri] if log_uri_exists else None

    def _get_output() -> Dict[str, Any]:
        storage = BlobStorage.from_account_key(
            os.path.dirname(output_uri),
            account_key=settings.blob_account_key,
            account_url=settings.blob_account_url,
        )
        return json.loads(storage.read_text(os.path.basename(output_uri)))

    if msg.task_result_type == TaskResultType.WAIT:
        output = _get_output()
        wait_result = WaitTaskResult.parse_obj(output)

        return HandledTaskResult(result=wait_result, log_uris=log_uris)
    elif msg.task_result_type == TaskResultType.COMPLETED:
        output = _get_output()
        result = CompletedTaskResult.parse_obj(output)

        # Handle notifications
        if result.notifications:
            with SubmitClient(settings.submit_settings) as submit_client:
                for notification in result.notifications:
                    notification_submit_msg = NotificationSubmitMessage(
                        notification=notification,
                        target_environment=msg.target_environment,
                        processing_id=msg.run_record_id,
                    )
                    submit_client.submit_notification(notification_submit_msg)

        return HandledTaskResult(
            result=CompletedTaskResult(output=output), log_uris=log_uris
        )
    else:
        return HandledTaskResult(result=FailedTaskResult(), log_uris=log_uris)


def update_record(
    msg: UpdateRecordMessage, event_logger: RunLogger
) -> UpdateRecordResult:
    settings = ExecutorSettings.get()
    update = msg.update

    try:

        # Workflow Run Group

        if isinstance(update, CreateWorkflowRunGroupRecordUpdate):
            event_logger.info("Createing workflow run group...")
            with settings.get_workflow_run_group_record_table() as wrg_table:
                wrg_table.insert_record(update.record)
        elif isinstance(update, WorkflowRunGroupRecordUpdate):
            event_logger.info(
                f"Updating workflow run group record status to {update.status}."
            )
            with settings.get_workflow_run_group_record_table() as wrg_table:
                wrg_record = wrg_table.get_record(
                    dataset=update.dataset, group_id=update.group_id
                )
                if not wrg_record:
                    return UpdateRecordResult(
                        error="Record not found.",
                    )
                wrg_record.set_update_time()
                update.update_record(wrg_record)
                wrg_table.update_record(wrg_record)

        # Workflow Run

        elif isinstance(update, CreateWorkflowRunRecordUpdate):
            event_logger.info("Creating workflow run ...")
            with settings.get_workflow_run_record_table() as wr_table:
                wr_table.insert_record(update.record)
        elif isinstance(update, WorkflowRunRecordUpdate):
            event_logger.info(
                f"Updating workflow run record status to {update.status}."
            )
            with settings.get_workflow_run_record_table() as wr_table:
                wr_record = wr_table.get_record(update.get_run_record_id())
                if not wr_record:
                    return UpdateRecordResult(error="Record not found.")
                wr_record.set_update_time()
                update.update_record(wr_record)
                wr_table.update_record(wr_record)

        # Job Run

        elif isinstance(update, CreateJobRunRecordUpdate):
            event_logger.info("Creating job run ...")
            with settings.get_job_run_record_table() as jr_table:
                jr_table.insert_record(update.record)
        elif isinstance(update, JobRunRecordUpdate):
            event_logger.info(f"Updating job run record status to {update.status}.")
            with settings.get_job_run_record_table() as jr_table:
                jr_record = jr_table.get_record(update.get_run_record_id())
                if not jr_record:
                    return UpdateRecordResult(error="Record not found.")
                jr_record.set_update_time()
                update.update_record(jr_record)
                jr_table.update_record(jr_record)

        # Task Run

        elif isinstance(update, CreateTaskRunRecordUpdate):
            event_logger.info("Creating task run ...")
            with settings.get_task_run_record_table() as tr_table:
                tr_table.insert_record(update.record)
        else:
            with settings.get_task_run_record_table() as tr_table:
                event_logger.info(
                    f"Updating task run record status to {update.status}."
                )
                tr_record = tr_table.get_record(update.get_run_record_id())
                if not tr_record:
                    return UpdateRecordResult(error="Record not found.")
                tr_record.set_update_time()
                update.update_record(tr_record)
                tr_table.update_record(tr_record)

        return UpdateRecordResult()
    except Exception as e:
        return UpdateRecordResult(error=str(e))


def send_notification(
    message: NotificationSubmitMessage, event_logger: RunLogger
) -> NotificationSubmitResult:
    event_logger.info(
        f"Sending notification of type {message.notification.event.type}..."
    )
    settings = ExecutorSettings.get()
    try:
        with QueueService.from_connection_string(
            connection_string=settings.notification_queue.connection_string,
            queue_name=settings.notification_queue.queue_name,
        ) as queue:
            msg_id = queue.send_message(message.dict())
            event_logger.info(f"Notification sent, queue id {msg_id}")
    except Exception as e:
        return NotificationSubmitResult(error=str(e))
    return NotificationSubmitResult()
