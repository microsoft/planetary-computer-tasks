"""
Integration tests that tests submitting an Ingest task.
Monitors the task status and ensures the
STAC Collection and Items were successfully created/updated
in the development database.
"""
import time
from pathlib import Path
from typing import Optional

from pctasks.core.constants import DEFAULT_LOG_CONTAINER
from pctasks.core.models.base import RunRecordId
from pctasks.core.models.record import (
    JobRunStatus,
    TaskRunStatus,
    WorkflowRunRecord,
    WorkflowRunStatus,
)
from pctasks.core.models.workflow import WorkflowSubmitMessage
from pctasks.core.storage.blob import BlobStorage
from pctasks.dev.env import (
    PCTASKS_BLOB_ACCOUNT_KEY_ENV_VAR,
    PCTASKS_BLOB_ACCOUNT_NAME_ENV_VAR,
    PCTASKS_BLOB_ACCOUNT_URL_ENV_VAR,
    get_dev_env,
)
from pctasks.dev.tables import (
    get_job_run_record_table,
    get_task_run_record_table,
    get_workflow_run_record_table,
)
from pctasks.execute.utils import get_exec_log_path, get_run_log_path
from pctasks.submit.client import SubmitClient
from pctasks.submit.settings import SubmitSettings
from pctasks.submit.template import template_workflow_file

HERE = Path(__file__).parent
WORKFLOWS = HERE / ".." / "workflows"
TEST_DATA = HERE / ".." / "data-files"

TIMEOUT_SECONDS = 10


def test_local():
    """Integration test against local resources."""

    # Template
    workflow = template_workflow_file(WORKFLOWS / "ingest-collection.yaml")

    job = list(workflow.jobs.values())[0]
    job_id = job.id
    assert job_id
    task_id = job.tasks[0].id

    submit_message = WorkflowSubmitMessage(
        workflow=workflow,
    )

    submit_settings = SubmitSettings.get()
    with SubmitClient(submit_settings) as submit_client:
        run_id = submit_client.submit_workflow(submit_message)

    print(f"Submitted workflow with id: {run_id}")

    print(submit_message.to_yaml())

    with get_workflow_run_record_table() as workflow_run_record_table:
        tic = time.perf_counter()
        tok = time.perf_counter()
        workflow_run_record: Optional[WorkflowRunRecord] = None
        while (
            workflow_run_record is None
            or workflow_run_record.status
            not in [WorkflowRunStatus.COMPLETED, WorkflowRunStatus.FAILED]
        ) and tok - tic < TIMEOUT_SECONDS:
            print(f"waiting for task run record... ({tok - tic:.0f} s)".format(tok))
            workflow_run_record = workflow_run_record_table.get_record(
                submit_message.get_run_record_id()
            )
            time.sleep(1)
            tok = time.perf_counter()

    if (
        workflow_run_record
        and workflow_run_record.status == WorkflowRunStatus.COMPLETED
    ):
        with get_job_run_record_table() as job_run_record_table:
            job_run_record = job_run_record_table.get_record(
                RunRecordId(job_id=job_id, run_id=run_id)
            )
            assert job_run_record
            assert job_run_record.status == JobRunStatus.COMPLETED

        with get_task_run_record_table() as task_run_record_table:
            task_run_record = task_run_record_table.get_record(
                RunRecordId(job_id=job_id, task_id=task_id, run_id=run_id)
            )
            assert task_run_record
            assert task_run_record.status == WorkflowRunStatus.COMPLETED
    else:
        exec_log_path = get_exec_log_path(job_id=job_id, task_id=task_id, run_id=run_id)
        run_log_path = get_run_log_path(job_id=job_id, task_id=task_id, run_id=run_id)

        log_storage = BlobStorage.from_account_key(
            f"blob://{get_dev_env(PCTASKS_BLOB_ACCOUNT_NAME_ENV_VAR)}"
            f"/{DEFAULT_LOG_CONTAINER}",
            account_key=get_dev_env(PCTASKS_BLOB_ACCOUNT_KEY_ENV_VAR),
            account_url=get_dev_env(PCTASKS_BLOB_ACCOUNT_URL_ENV_VAR),
        )

        if log_storage.file_exists(exec_log_path):
            print(" -- Exec log: --")
            print(log_storage.read_text(exec_log_path))
            print(" -- End exec log: --")

            if log_storage.file_exists(run_log_path):
                print(" -- Run log: --")
                print(log_storage.read_text(run_log_path))
                print(" -- End run log: --")
            else:
                print(f"No run log found at {run_log_path}")
        else:
            print(f"No exec log found at {log_storage.get_uri(exec_log_path)}")

        if workflow_run_record:
            assert workflow_run_record.status == TaskRunStatus.COMPLETED
        else:
            raise Exception("Timeout while waiting for run record")
