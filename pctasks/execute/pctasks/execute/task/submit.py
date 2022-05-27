import logging
from typing import List, Optional


from pctasks.core.logging import RunLogger
from pctasks.execute.executor import get_executor
from pctasks.execute.executor.base import TaskExecutor
from pctasks.execute.models import (
    SuccessfulSubmitResult,
    TaskSubmitMessage,
    TaskSubmitResult,
)
from pctasks.execute.settings import ExecutorSettings
from pctasks.execute.task.run_message import prepare_task

logger = logging.getLogger(__name__)


def submit_tasks(
    run_id: str,
    submit_msgs: List[TaskSubmitMessage],
    settings: ExecutorSettings,
    event_logger: Optional[RunLogger] = None,
    executor: Optional[TaskExecutor] = None,
) -> List[TaskSubmitResult]:
    """
    Process a submit message.

    Constructs the TaskRunMessage from the SubmitMessage
    and writes it to the TaskRun table.
    Then submits the TaskRunMessage to the executor.

    Args:
        submit_msgs: The submit messages to process.
        settings: The exec settings.
        run_id: The run id to use.
            If None, a new random run id is generated.
        event_logger: The event logger to use.
            If None, a new event logger is created.
        executor: The executor to use.
            If None, a new executor is created from settings.
            This is used for testing.

    Returns:
        The run ID.
    """
    # event_logger = event_logger or RunLogger(
    #     submit_msgs.get_run_record_id(), logger_id=ActivityNames.TASK_SUBMIT
    # )

    try:
        # Log exec info to task exec log.
        # exec_log_path = get_exec_log_path(
        #     submit_msgs.job_id, submit_msgs.config.id, run_id
        # )
        # log_blob_sas_token = generate_blob_sas(
        #     account_name=settings.blob_account_name,
        #     account_key=settings.blob_account_key,
        #     container_name=settings.log_blob_container,
        #     blob_name=exec_log_path,
        #     start=datetime.now(),
        #     expiry=datetime.utcnow() + timedelta(hours=24 * 7),
        #     permission=BlobSasPermissions(write=True),
        # )
        # log_storage = BlobStorage.from_uri(
        #     f"blob://{settings.blob_account_name}/{settings.log_blob_container}",
        #     sas_token=log_blob_sas_token,
        #     account_url=settings.blob_account_url,
        # )

        # with TaskLogger(log_storage, exec_log_path):
        # logger.info(
        #     f" == PCTasks: Executing job_id {submit_msgs.job_id} "
        #     f"task_id {submit_msgs.config.id} "
        #     f"run_id {run_id}"
        # )
        try:
            prepared_tasks = [prepare_task(
                submit_msg=submit_msg,
                run_id=run_id,
                settings=settings,
            ) for submit_msg in submit_msgs]

            executor = executor or get_executor(settings)
            executor_id = executor.submit(
                prepared_tasks,
                settings=settings,
            )

            # event_logger.log_event(TaskRunStatus.SUBMITTED)

            output_blob_config = run_msg.config.output_blob_config
            return [TaskSubmitResult(
                result=SuccessfulSubmitResult(
                    executor_id=executor_id,
                    signal_key=prepared_tasks[0].task_run_message.config.signal_key,
                    output_uri=output_blob_config.uri,
                    log_uri=run_msg.config.log_blob_config.uri,
                    output_account_url=output_blob_config.account_url,
                )
            )]
        except Exception as e:
            logger.exception(e)
            raise

    except Exception:
        # event_logger.log_event(
        #     TaskRunStatus.FAILED, message=f"Failed to process message: {e}"
        # )
        raise
