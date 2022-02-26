"""
Integration tests that tests submitting an Ingest task.
Monitors the task status and ensures the
STAC Collection and Items were successfully created/updated
in the development database.
"""
import time
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Optional

from pctasks.core.models.base import RunRecordId
from pctasks.core.models.record import WorkflowRunRecord, WorkflowRunStatus
from pctasks.core.models.workflow import WorkflowSubmitMessage
from pctasks.dev.tables import get_workflow_run_record_table
from pctasks.submit.client import SubmitClient
from pctasks.submit.settings import SubmitSettings
from pctasks.submit.template import template_workflow_file

HERE = Path(__file__).parent
WORKFLOWS = HERE / "workflows"
ASSETS_DIR = HERE / "data-files" / "simple-assets"

TIMEOUT_SECONDS = 20


def test_foreach_simple_workflow():
    # Template
    workflow = template_workflow_file(WORKFLOWS / "test-foreach-simple.yaml")

    with TemporaryDirectory() as tmp_dir:
        submit_message = WorkflowSubmitMessage(
            workflow=workflow,
            args={"output_dir": tmp_dir},
        )

        submit_settings = SubmitSettings.get()
        with SubmitClient(submit_settings) as submit_client:
            run_id = submit_client.submit_workflow(submit_message)

        print(f"Submitted workflow with id: {run_id}")

        with get_workflow_run_record_table() as workflow_run_record_table:
            tic = time.perf_counter()
            tok = time.perf_counter()
            workflow_run_record: Optional[WorkflowRunRecord] = None
            while (
                workflow_run_record is None
                or workflow_run_record.status
                not in [WorkflowRunStatus.COMPLETED, WorkflowRunStatus.FAILED]
            ) and tok - tic < TIMEOUT_SECONDS:
                print(
                    f"waiting for workflow run record... ({tok - tic:.0f} s)".format(
                        tok
                    )
                )
                workflow_run_record = workflow_run_record_table.get_record(
                    RunRecordId(
                        dataset_id=str(submit_message.workflow.dataset), run_id=run_id
                    )
                )
                time.sleep(1)
                tok = time.perf_counter()

        if workflow_run_record:
            print(workflow_run_record.to_yaml())

        assert (
            workflow_run_record
            and workflow_run_record.status == WorkflowRunStatus.COMPLETED
        )

        expected = {}

        for path in Path(ASSETS_DIR).rglob("*.*"):
            expected[path.name] = path.read_text()

        assert expected

        for path in Path(tmp_dir).rglob("*.*"):
            assert path.name in expected
            assert expected[path.name] == path.read_text()


def test_foreach_full_workflow():
    # Template
    workflow = template_workflow_file(WORKFLOWS / "test-foreach.yaml")

    with TemporaryDirectory() as tmp_dir:
        submit_message = WorkflowSubmitMessage(
            workflow=workflow,
            args={"output_dir": tmp_dir},
        )

        submit_settings = SubmitSettings.get()
        with SubmitClient(submit_settings) as submit_client:
            run_id = submit_client.submit_workflow(submit_message)

        print(f"Submitted workflow with id: {run_id}")

        with get_workflow_run_record_table() as workflow_run_record_table:
            tic = time.perf_counter()
            tok = time.perf_counter()
            workflow_run_record: Optional[WorkflowRunRecord] = None
            while (
                workflow_run_record is None
                or workflow_run_record.status
                not in [WorkflowRunStatus.COMPLETED, WorkflowRunStatus.FAILED]
            ) and tok - tic < TIMEOUT_SECONDS:
                print(
                    f"waiting for workflow run record... ({tok - tic:.0f} s)".format(
                        tok
                    )
                )
                workflow_run_record = workflow_run_record_table.get_record(
                    RunRecordId(
                        dataset_id=str(submit_message.workflow.dataset), run_id=run_id
                    )
                )
                time.sleep(1)
                tok = time.perf_counter()

        if workflow_run_record:
            print(workflow_run_record.to_yaml())

        assert (
            workflow_run_record
            and workflow_run_record.status == WorkflowRunStatus.COMPLETED
        )

        expected = {}

        for path in Path(ASSETS_DIR).rglob("*.*"):
            expected[path.name] = path.read_text()

        assert expected

        for path in Path(tmp_dir).rglob("*.*"):
            assert path.name in expected
            assert expected[path.name] == path.read_text()
