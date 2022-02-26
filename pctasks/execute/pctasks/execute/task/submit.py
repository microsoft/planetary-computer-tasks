import logging
from datetime import datetime, timedelta
from typing import Optional

from azure.storage.blob import BlobSasPermissions, generate_blob_sas

from pctasks.core.logging import RunLogger, TaskLogger
from pctasks.core.models.config import BlobConfig
from pctasks.core.models.record import TaskRunStatus
from pctasks.core.models.task import TaskRunMessage
from pctasks.core.storage.blob import BlobStorage, BlobUri
from pctasks.execute.constants import ActivityNames
from pctasks.execute.executor import get_executor
from pctasks.execute.executor.base import Executor
from pctasks.execute.models import (
    SuccessfulSubmitResult,
    TaskSubmitMessage,
    TaskSubmitResult,
)
from pctasks.execute.settings import ExecutorSettings
from pctasks.execute.task.run_message import submit_msg_to_task_run_msg
from pctasks.execute.utils import get_exec_log_path, get_task_input_path

logger = logging.getLogger(__name__)


def write_task_run_msg(
    run_msg: TaskRunMessage, settings: ExecutorSettings
) -> BlobConfig:
    """
    Write the task run message to the Task IO input file

    Returns a SAS token that can be used to read the table.
    """
    task_input_path = get_task_input_path(
        job_id=run_msg.config.job_id,
        task_id=run_msg.config.task_id,
        run_id=run_msg.config.run_id,
    )
    task_input_uri = BlobUri(
        f"blob://{settings.blob_account_name}/"
        f"{settings.log_blob_container}/"
        f"{task_input_path}"
    )

    task_io_storage = BlobStorage.from_account_key(
        f"blob://{task_input_uri.storage_account_name}/{task_input_uri.container_name}",
        account_key=settings.blob_account_key,
        account_url=settings.blob_account_url,
    )

    task_io_storage.write_text(
        task_input_path,
        run_msg.encoded(),
    )

    input_blob_sas_token = generate_blob_sas(
        account_name=settings.blob_account_name,
        account_key=settings.blob_account_key,
        container_name=settings.log_blob_container,
        blob_name=task_input_path,
        start=datetime.now(),
        expiry=datetime.utcnow() + timedelta(hours=24 * 7),
        permission=BlobSasPermissions(read=True),
    )

    return BlobConfig(
        uri=str(task_input_uri),
        sas_token=input_blob_sas_token,
        account_url=settings.blob_account_url,
    )


def submit_task(
    submit_msg: TaskSubmitMessage,
    settings: ExecutorSettings,
    event_logger: Optional[RunLogger] = None,
    executor: Optional[Executor] = None,
) -> TaskSubmitResult:
    """
    Process a submit message.

    Constructs the TaskRunMessage from the SubmitMessage
    and writes it to the TaskRun table.
    Then submits the TaskRunMessage to the executor.

    Args:
        submit_msg: The submit message to process.
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
    run_id = submit_msg.run_id
    event_logger = event_logger or RunLogger(
        submit_msg.get_run_record_id(), logger_id=ActivityNames.TASK_SUBMIT
    )

    try:
        # Log exec info to task exec log.
        exec_log_path = get_exec_log_path(
            submit_msg.job_id, submit_msg.config.id, run_id
        )
        log_blob_sas_token = generate_blob_sas(
            account_name=settings.blob_account_name,
            account_key=settings.blob_account_key,
            container_name=settings.log_blob_container,
            blob_name=exec_log_path,
            start=datetime.now(),
            expiry=datetime.utcnow() + timedelta(hours=24 * 7),
            permission=BlobSasPermissions(write=True),
        )
        log_storage = BlobStorage.from_uri(
            f"blob://{settings.blob_account_name}/{settings.log_blob_container}",
            sas_token=log_blob_sas_token,
            account_url=settings.blob_account_url,
        )

        with TaskLogger(log_storage, exec_log_path):
            logger.info(
                f" == PCTasks: Executing job_id {submit_msg.job_id} "
                f"task_id {submit_msg.config.id} "
                f"run_id {run_id}"
            )
            try:
                run_msg = submit_msg_to_task_run_msg(
                    submit_msg=submit_msg,
                    run_id=run_id,
                    settings=settings,
                )

                task_input_blob_config = write_task_run_msg(run_msg, settings)

                executor = executor or get_executor(settings)
                executor_id = executor.submit(
                    submit_msg=submit_msg,
                    run_msg=run_msg,
                    task_input_blob_config=task_input_blob_config,
                    settings=settings,
                )

                event_logger.log_event(TaskRunStatus.SUBMITTED)

                output_blob_config = run_msg.config.output_blob_config
                return TaskSubmitResult(
                    result=SuccessfulSubmitResult(
                        executor_id=executor_id,
                        signal_key=run_msg.config.signal_key,
                        output_uri=output_blob_config.uri,
                        log_uri=run_msg.config.log_blob_config.uri,
                        output_account_url=output_blob_config.account_url,
                    )
                )
            except Exception as e:
                logger.exception(e)
                raise

    except Exception as e:
        event_logger.log_event(
            TaskRunStatus.FAILED, message=f"Failed to process message: {e}"
        )
        raise
