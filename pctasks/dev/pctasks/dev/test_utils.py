import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from click.testing import CliRunner, Result
from pypgstac.db import PgstacDB

from pctasks.cli.cli import pctasks_cmd
from pctasks.client.client import PCTasksClient
from pctasks.client.errors import NotFoundError
from pctasks.client.settings import ClientSettings
from pctasks.client.workflow.template import template_workflow_dict
from pctasks.core.constants import DEFAULT_LOG_CONTAINER, DEFAULT_TASK_IO_CONTAINER
from pctasks.core.models.run import (
    JobPartitionRunRecord,
    JobRunStatus,
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
from pctasks.core.models.workflow import (
    Workflow,
    WorkflowDefinition,
    WorkflowSubmitRequest,
)
from pctasks.dataset.models import ChunkOptions, StorageConfig
from pctasks.dataset.splits.models import CreateSplitsOptions
from pctasks.dataset.template import template_dataset_file
from pctasks.dataset.workflow import (
    create_ingest_collection_workflow,
    create_process_items_workflow,
)
from pctasks.dev.blob import temp_azurite_blob_storage
from pctasks.dev.config import get_blob_config
from pctasks.dev.db import temp_pgstac_db
from pctasks.ingest.constants import DB_CONNECTION_STRING_ENV_VAR
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
    if result.stderr and not silent:
        print(result.stderr, file=sys.stderr)
    if result.exception is not None and not catch_exceptions:
        raise CliTestError("Test code threw an exception") from result.exception
    return result


@dataclass
class TestWorkflowRunRecords:
    workflow: Workflow
    workflow_run: WorkflowRunRecord
    job_partition_runs: Dict[str, List[JobPartitionRunRecord]]
    timeout: bool = False

    def print(self) -> None:
        print("________________________________________")
        print(f"Workflow: {self.workflow_run.run_id}:")
        print("----------------------------------------")
        print(self.workflow_run.to_yaml())
        print("++++++++++++++++++++++++++++++++++++++++")
        for job in self.workflow_run.jobs:
            print(f"Job: {job.job_id}:")
            print("----------------------------------------")
            print(job.to_yaml())
            print("++++++++++++++++++++++++++++++++++++++++")
            job_parts = self.job_partition_runs.get(job.job_id, [])
            if not job_parts:
                print(f"No job partition runs for job {job.job_id}")
            for job_part in job_parts:
                print(f"Job Partition: {job_part.partition_id}:")
                print("----------------------------------------")
                print(job_part.to_yaml())
                print("++++++++++++++++++++++++++++++++++++++++")
                for task in job_part.tasks:
                    print(f"Task: {task.task_id} ({task.job_id}):")
                    print("----------------------------------------")
                    print(task.to_yaml())
                    print("++++++++++++++++++++++++++++++++++++++++")
        print("________________________________________")


def wait_for_test_workflow_run(
    run_id: str, timeout_seconds: int = 10
) -> TestWorkflowRunRecords:
    print(f"Waiting for test workflow run {run_id} to complete...")
    workflow_run: Optional[WorkflowRunRecord] = None

    client = PCTasksClient()

    tic = time.perf_counter()
    tok = time.perf_counter()
    while (
        workflow_run is None
        or workflow_run.status
        not in [WorkflowRunStatus.COMPLETED, WorkflowRunStatus.FAILED]
    ) and tok - tic < timeout_seconds:
        if not workflow_run:
            print(f"waiting for workflow run record... ({tok - tic:.0f} s)".format(tok))
        else:
            print(
                f"Waiting on workflow run with status {workflow_run.status}... "
                f"({tok - tic:.0f} s)".format(tok)
            )
        try:
            workflow_run = client.get_workflow_run(run_id)
        except NotFoundError:
            pass

        time.sleep(1)
        tok = time.perf_counter()

    if workflow_run:
        workflow_record = client.get_workflow(workflow_run.workflow_id)
        if not workflow_record:
            raise Exception(f"Workflow {workflow_run.workflow_id} not found")
        job_runs = workflow_run.jobs

        job_part_runs: Dict[str, List[JobPartitionRunRecord]] = {}
        for job_run in job_runs:
            job_part_runs[job_run.job_id] = list(
                client.list_job_partition_runs(run_id, job_run.job_id)
            )

        return TestWorkflowRunRecords(
            workflow=workflow_record.workflow,
            workflow_run=workflow_run,
            job_partition_runs=job_part_runs,
            timeout=tok - tic >= timeout_seconds,
        )
    else:
        raise Exception(f"Timeout while waiting for workflow {run_id}")


def _check_workflow(
    run_id: str, timeout_seconds: int = 10
) -> Tuple[bool, TestWorkflowRunRecords]:
    workflow_record = wait_for_test_workflow_run(run_id, timeout_seconds)
    failed = workflow_record.workflow_run.status != WorkflowRunStatus.COMPLETED
    if failed:
        print(
            f"Workflow run {run_id} failed. "
            f"Status: {workflow_record.workflow_run.status}"
        )
        if workflow_record.timeout:
            print(f"TIMEOUT while waiting for workflow {run_id}")
        print("Workflow:")
        print(workflow_record.workflow.to_yaml())
    for job_run in workflow_record.workflow_run.jobs:
        job_failed = job_run.status != JobRunStatus.COMPLETED
        if job_failed:
            print(f"Job {job_run.job_id} failed. Status: {job_run.status}")
            for error in job_run.errors or []:
                print(f" -- {error}")
        failed |= job_failed
        job_partitions = workflow_record.job_partition_runs.get(job_run.job_id)
        if not job_partitions:
            print(f"No job partitions for job {job_run.job_id}")
        else:
            for job_part_run in job_partitions:
                for task_run in job_part_run.tasks:
                    task_failed = task_run.status != TaskRunStatus.COMPLETED
                    if task_failed:
                        print(
                            f"Task {task_run.task_id} failed in job "
                            f"{job_run.job_id}:{job_part_run.partition_id}."
                        )
                        for error in task_run.errors or []:
                            print(f" --- {error}")
                    failed |= task_failed
                    if task_failed:
                        client = PCTasksClient()

                        log = client.get_task_log(
                            run_id=run_id,
                            job_id=job_run.job_id,
                            partition_id=task_run.partition_id,
                            task_id=task_run.task_id,
                        )
                        if log:
                            print("\t\t---------- TASK LOG ----------")
                            print(log)
                            print(f"\t\t-- End log  for task {task_run.task_id} --")
                        else:
                            print(f"No run log found for task {task_run.task_id}")

    return (failed, workflow_record)


def assert_workflow_is_successful(
    run_id: str, timeout_seconds: int = 10
) -> TestWorkflowRunRecords:
    failed, records = _check_workflow(run_id, timeout_seconds)
    assert not failed
    return records


def assert_workflow_fails(
    run_id: str, timeout_seconds: int = 10
) -> TestWorkflowRunRecords:
    failed, records = _check_workflow(run_id, timeout_seconds)
    assert failed
    return records


def run_workflow(
    workflow: Union[str, WorkflowDefinition],
    args: Optional[Dict[str, Any]] = None,
    base_path: Union[str, Path] = Path.cwd(),
) -> str:
    """Runs a workflow from either a YAML string or WorkflowDefinition object.
    Uses the default submit settings.
    Returns the run_id
    """
    workflow = (
        WorkflowDefinition.from_yaml(workflow)
        if isinstance(workflow, str)
        else workflow
    )
    templated_workflow = template_workflow_dict(workflow.dict(), base_path=base_path)
    submit_settings = ClientSettings.get()
    submit_settings.confirmation_required = False
    submit_response = PCTasksClient(submit_settings).upsert_and_submit_workflow(
        workflow_definition=templated_workflow, request=WorkflowSubmitRequest(args=args)
    )
    return submit_response.run_id


def run_workflow_from_file(
    workflow_path: Union[str, Path],
    args: Optional[Dict[str, Any]] = None,
) -> str:
    """Runs a workflow from a YAML file at workflow_path.
    Uses the default submit settings.
    Returns the run_id
    """
    return run_workflow(
        Path(workflow_path).read_text(),
        args=args,
        base_path=Path(workflow_path).parent,
    )


def run_test_task(
    args: Dict[str, Any],
    task: str,
    tokens: Optional[Dict[str, StorageAccountTokens]] = None,
) -> Union[CompletedTaskResult, WaitTaskResult]:

    job_id = "unit-test-job"
    task_id = "task-unit-test"
    run_id = "test_task_func"

    log_path = f"{job_id}/{task_id}/{run_id}.log"
    status_update_path = f"{job_id}/{task_id}/{run_id}/status.txt"
    output_path = f"{job_id}/{task_id}/{run_id}-output.json"

    msg = TaskRunMessage(
        args=args,
        config=TaskRunConfig(
            run_id=run_id,
            job_id=job_id,
            partition_id="0",
            task_id=task_id,
            image="TESTIMAGE:latest",
            tokens=tokens,
            task=task,
            status_blob_config=get_blob_config(
                DEFAULT_TASK_IO_CONTAINER, status_update_path
            ),
            log_blob_config=get_blob_config(DEFAULT_LOG_CONTAINER, log_path),
            output_blob_config=get_blob_config(DEFAULT_TASK_IO_CONTAINER, output_path),
        ),
    )

    result = run_task(msg)
    if isinstance(result, CompletedTaskResult):
        return result
    else:
        assert isinstance(result, WaitTaskResult)
        return result


def run_process_items_workflow(
    dataset_path: Union[Path, str],
    collection_id: Optional[str] = None,
    args: Optional[Dict[str, str]] = None,
    check_items: Optional[Callable[[List[Dict[str, Any]]], None]] = None,
    timeout_seconds: int = 300,
    splits_limit: int = 1,
    chunks_limit: int = 2,
    image: Optional[str] = None,
) -> None:
    with temp_pgstac_db() as conn_str_info:
        with temp_azurite_blob_storage() as root_storage:
            chunks_storage = root_storage.get_substorage("chunks")

            dataset = template_dataset_file(Path(dataset_path), args)

            if image:
                dataset.image = image

            # Modify dataset for tests
            if not dataset.environment:
                dataset.environment = {}
            dataset.environment[DB_CONNECTION_STRING_ENV_VAR] = conn_str_info.remote

            for collection_config in dataset.collections:
                collection_config.chunk_storage = StorageConfig(
                    uri=chunks_storage.get_uri()
                )

            collection_config = dataset.get_collection(collection_id)
            collection_id = collection_config.id

            # Ingest collection
            _ingest_submit_result = PCTasksClient().upsert_and_submit_workflow(
                workflow_definition=create_ingest_collection_workflow(
                    dataset, collection_config
                ),
                request=WorkflowSubmitRequest(
                    args=args,
                ),
            )
            assert_workflow_is_successful(
                _ingest_submit_result.run_id,
                timeout_seconds=timeout_seconds,
            )

            with PgstacDB(conn_str_info.local) as db:
                res = db.query_one(
                    "SELECT id FROM collections WHERE id=%s",
                    (collection_id,),
                )
                assert res == collection_id

            # Process items
            _items_submit_result = PCTasksClient().upsert_and_submit_workflow(
                workflow_definition=create_process_items_workflow(
                    dataset,
                    collection_config,
                    "test-chunkset-id",
                    create_splits_options=CreateSplitsOptions(limit=splits_limit),
                    chunk_options=ChunkOptions(limit=chunks_limit),
                ),
                request=WorkflowSubmitRequest(args=args),
            )
            assert_workflow_is_successful(
                _items_submit_result.run_id,
                timeout_seconds=timeout_seconds,
            )

            with PgstacDB(conn_str_info.local) as db:
                res = db.search(
                    {
                        "filter": {
                            "op": "=",
                            "args": [{"property": "collection"}, collection_id],
                        }
                    }
                )
                assert isinstance(res, str)
                item_dicts = json.loads(res)["features"]
                assert item_dicts
                if check_items:
                    check_items(item_dicts)
