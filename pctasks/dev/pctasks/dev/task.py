from typing import Any, Dict, Optional, Union

from pctasks.core.constants import (
    DEFAULT_LOG_CONTAINER,
    DEFAULT_SIGNAL_QUEUE_NAME,
    DEFAULT_TASK_IO_CONTAINER,
    DEFAULT_TASK_RUN_RECORD_TABLE_NAME,
)
from pctasks.core.models.base import RunRecordId
from pctasks.core.models.record import TaskRunRecord, TaskRunStatus
from pctasks.core.models.task import (
    CompletedTaskResult,
    TaskRunConfig,
    TaskRunMessage,
    WaitTaskResult,
)
from pctasks.core.models.tokens import StorageAccountTokens
from pctasks.dev.config import get_blob_config, get_queue_config, get_table_config
from pctasks.dev.tables import get_task_run_record_table
from pctasks.task.run import run_task


def run_test_task(
    args: Dict[str, Any],
    task: str,
    tokens: Optional[Dict[str, StorageAccountTokens]] = None,
) -> Union[CompletedTaskResult, WaitTaskResult]:
    job_id = "unit-test-job"
    task_id = "task-unit-test"
    run_id = "test_task_func"

    run_record_id = RunRecordId(
        job_id=job_id,
        task_id=task_id,
        run_id=run_id,
    )

    with get_task_run_record_table() as task_run_table:
        task_run_table.upsert_record(
            TaskRunRecord(
                run_id=run_record_id.run_id,
                job_id=job_id,
                task_id=task_id,
                status=TaskRunStatus.SUBMITTED,
            )
        )

        log_path = f"{job_id}/{task_id}/{run_id}.log"
        output_path = f"{job_id}/{task_id}/{run_id}-output.json"

        msg = TaskRunMessage(
            args=args,
            config=TaskRunConfig(
                run_id=run_id,
                job_id=job_id,
                task_id=task_id,
                signal_key="signal-key",
                signal_target_id="target-id",
                image="TESTIMAGE:latest",
                tokens=tokens,
                task=task,
                signal_queue=get_queue_config(DEFAULT_SIGNAL_QUEUE_NAME),
                task_runs_table_config=get_table_config(
                    DEFAULT_TASK_RUN_RECORD_TABLE_NAME
                ),
                log_blob_config=get_blob_config(DEFAULT_LOG_CONTAINER, log_path),
                output_blob_config=get_blob_config(
                    DEFAULT_TASK_IO_CONTAINER, output_path
                ),
            ),
        )

        result = run_task(msg)
        if isinstance(result, CompletedTaskResult):
            record = task_run_table.get_record(
                run_record_id=run_record_id,
            )
            assert record
            assert record.status == TaskRunStatus.COMPLETED

            return result
        else:
            assert isinstance(result, WaitTaskResult)
            return result
