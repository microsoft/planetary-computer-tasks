import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union

from click.testing import CliRunner, Result

from pctasks.cli.cli import pctasks_cmd
from pctasks.core.constants import (
    DEFAULT_LOG_CONTAINER,
    DEFAULT_TASK_IO_CONTAINER,
    DEFAULT_TASK_RUN_RECORD_TABLE_NAME,
)
from pctasks.core.models.base import RunRecordId
from pctasks.core.models.record import (
    JobRunRecord,
    JobRunStatus,
    TaskRunRecord,
    TaskRunStatus,
    WorkflowRunRecord,
    WorkflowRunStatus,
)
from pctasks.core.models.task import (
    CompletedTaskResult,
    TaskRunConfig,
    TaskRunMessage,
    WaitTaskResult,
)
from pctasks.core.models.tokens import StorageAccountTokens
from pctasks.core.storage.blob import BlobStorage
from pctasks.dev.config import get_blob_config, get_table_config
from pctasks.dev.env import (
    PCTASKS_BLOB_ACCOUNT_KEY_ENV_VAR,
    PCTASKS_BLOB_ACCOUNT_NAME_ENV_VAR,
    PCTASKS_BLOB_ACCOUNT_URL_ENV_VAR,
    get_dev_env,
)
from pctasks.dev.tables import get_task_run_record_table
from pctasks.run.utils import get_run_log_path
from pctasks.task.run import run_task


class CliTestError(Exception):
    pass


def run_pctasks(
    cmd: List[Any], catch_exceptions: bool = False, silent: bool = False
) -> Result:
    runner = CliRunner(mix_stderr=False)

    if len(cmd) == 0:
        raise Exception("Empty command")

    result = runner.invoke(pctasks_cmd, [str(c) for c in cmd], catch_exceptions=True)
    if result.output and not silent:
        print(result.output)
    if result.exception is not None and not catch_exceptions:
        raise CliTestError("Test code threw an exception") from result.exception
    return result


@dataclass
class TestJobRunRecords:
    job_record: JobRunRecord
    tasks: Dict[str, TaskRunRecord]


@dataclass
class TestWorkflowRunRecords:
    workflow_record: WorkflowRunRecord
    jobs: Dict[str, TestJobRunRecords]


def wait_for_test_workflow_run(
    run_id: str, timeout_seconds: int = 10
) -> TestWorkflowRunRecords:
    print(f"Waiting for test workflow run {run_id} to complete...")
    workflow_run_record: Optional[WorkflowRunRecord] = None
    tic = time.perf_counter()
    tok = time.perf_counter()
    while (
        workflow_run_record is None
        or workflow_run_record.status
        not in [WorkflowRunStatus.COMPLETED, WorkflowRunStatus.FAILED]
    ) and tok - tic < timeout_seconds:
        if not workflow_run_record:
            print(f"waiting for workflow run record... ({tok - tic:.0f} s)".format(tok))
        else:
            print(
                f"Retrying workflow run with status {workflow_run_record.status}... "
                f"({tok - tic:.0f} s)".format(tok)
            )
        workflow_record_result = run_pctasks(
            ["records", "fetch", "workflow", run_id], catch_exceptions=True, silent=True
        )

        if workflow_record_result.exit_code == 0:
            workflow_run_record = WorkflowRunRecord.from_yaml(
                workflow_record_result.output
            )
        else:
            print(f"Retrying, exit code: {workflow_record_result.exit_code}")

        time.sleep(1)
        tok = time.perf_counter()

    if workflow_run_record:
        list_jobs_result = run_pctasks(
            ["records", "list", "jobs", "--ids", run_id],
            catch_exceptions=True,
            silent=True,
        )

        assert list_jobs_result.exit_code == 0
        job_ids = list_jobs_result.output.splitlines()

        job_records: Dict[str, TestJobRunRecords] = {}
        for job_id in job_ids:
            job_record_result = run_pctasks(
                ["records", "fetch", "job", job_id, run_id],
                catch_exceptions=True,
                silent=True,
            )

            assert job_record_result.exit_code == 0
            job_record = JobRunRecord.from_yaml(job_record_result.output)

            list_tasks_result = run_pctasks(
                ["records", "list", "tasks", "--ids", job_id, run_id],
                catch_exceptions=True,
                silent=True,
            )

            assert list_tasks_result.exit_code == 0
            task_ids = list_tasks_result.output.splitlines()

            task_records: Dict[str, TaskRunRecord] = {}
            for task_id in task_ids:
                task_record_result = run_pctasks(
                    ["records", "fetch", "task", job_id, task_id, run_id],
                    catch_exceptions=True,
                    silent=True,
                )

                assert task_record_result.exit_code == 0
                task_records[task_id] = TaskRunRecord.from_yaml(
                    task_record_result.output
                )

            job_records[job_id] = TestJobRunRecords(job_record, task_records)

        return TestWorkflowRunRecords(workflow_run_record, job_records)
    else:
        raise Exception("Timeout while waiting for run record")


def assert_workflow_is_successful(
    run_id: str, timeout_seconds: int = 10
) -> TestWorkflowRunRecords:
    workflow_run_records = wait_for_test_workflow_run(run_id, timeout_seconds)
    failed = workflow_run_records.workflow_record.status != WorkflowRunStatus.COMPLETED
    for job_id, job_records in workflow_run_records.jobs.items():
        job_failed = job_records.job_record.status != JobRunStatus.COMPLETED
        if job_failed:
            print(f"Job {job_id} failed. Status: {job_records.job_record.status}")
        failed |= job_failed
        for task_id, task_record in job_records.tasks.items():
            task_failed = task_record.status != TaskRunStatus.COMPLETED
            if task_failed:
                print(f"Task {task_id} failed")
            failed |= task_failed
            if task_failed:
                run_log_path = get_run_log_path(
                    job_id=job_id, task_id=task_id, run_id=run_id
                )

                log_storage = BlobStorage.from_account_key(
                    f"blob://{get_dev_env(PCTASKS_BLOB_ACCOUNT_NAME_ENV_VAR)}"
                    f"/{DEFAULT_LOG_CONTAINER}",
                    account_key=get_dev_env(PCTASKS_BLOB_ACCOUNT_KEY_ENV_VAR),
                    account_url=get_dev_env(PCTASKS_BLOB_ACCOUNT_URL_ENV_VAR),
                )

                if log_storage.file_exists(run_log_path):
                    print(" -- Run log: --")
                    print(log_storage.read_text(run_log_path))
                    print(" -- End run log: --")
                else:
                    print(f"No run log found at {run_log_path}")

    if failed:
        raise Exception("Workflow failed")

    return workflow_run_records


def run_test_task(
    args: Dict[str, Any],
    task: str,
    tokens: Optional[Dict[str, StorageAccountTokens]] = None,
    task_run_config_options: Optional[Dict[str, Any]] = None
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
        task_run_config_options = task_run_config_options or {}

        msg = TaskRunMessage(
            args=args,
            config=TaskRunConfig(
                run_id=run_id,
                job_id=job_id,
                task_id=task_id,
                image="TESTIMAGE:latest",
                tokens=tokens,
                task=task,
                task_runs_table_config=get_table_config(
                    DEFAULT_TASK_RUN_RECORD_TABLE_NAME
                ),
                log_blob_config=get_blob_config(DEFAULT_LOG_CONTAINER, log_path),
                output_blob_config=get_blob_config(
                    DEFAULT_TASK_IO_CONTAINER, output_path
                ),
                **task_run_config_options
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
