import logging
from collections import defaultdict
from dataclasses import dataclass
from itertools import groupby
from threading import Lock
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import cachetools
from azure.core.exceptions import HttpResponseError

from pctasks.core.models.run import TaskRunStatus
from pctasks.core.models.task import TaskDefinition
from pctasks.core.utils import map_opt
from pctasks.run.batch.client import BatchClient
from pctasks.run.batch.model import BatchJobState, BatchTaskId
from pctasks.run.batch.task import BatchTask
from pctasks.run.batch.utils import make_valid_batch_id
from pctasks.run.constants import MAX_MISSING_POLLS
from pctasks.run.models import (
    FailedTaskSubmitResult,
    PreparedTaskSubmitMessage,
    SuccessfulTaskSubmitResult,
    TaskPollResult,
)
from pctasks.run.settings import BatchSettings, RunSettings
from pctasks.run.task.base import TaskRunner

logger = logging.getLogger(__name__)

BATCH_POOL_ID_TAG = "batch_pool_id"

JOB_ID_KEY = "job_id"


class BatchTaskRunnerError(Exception):
    pass


job_locks: Dict[str, Lock] = defaultdict(Lock)
failed_task_lock = Lock()


def get_pool_id(tags: Optional[Dict[str, str]], batch_settings: BatchSettings) -> str:
    return (tags or {}).get(BATCH_POOL_ID_TAG, batch_settings.default_pool_id)


def create_batch_task_id(part_id: str, task_id: str) -> str:
    """Create a Batch task ID from a partition ID and a task ID.

    Create unique batch task ids for a partition by including the partition
    ID into the task ID.
    """
    return f"{task_id}:{part_id}"


def make_batch_job_id(dataset_id: str, job_id: str, run_id: str, pool_id: str) -> str:
    job_id = f"{dataset_id}:{job_id}:{run_id}:{pool_id}"
    return make_valid_batch_id(job_id)


@dataclass(frozen=True)
class BatchJobInfo:
    job_prefix: str
    pool_id: str


@dataclass(frozen=True)
class BatchTaskInfo:
    task: BatchTask
    index: int


class BatchTaskRunner(TaskRunner):
    def __init__(self, settings: RunSettings):
        super().__init__(settings)
        self._batch_client: Optional[BatchClient] = None
        self.response_cache: cachetools.Cache = cachetools.TTLCache(
            maxsize=100, ttl=self.settings.batch_cache_seconds
        )

    def __enter__(self) -> "BatchTaskRunner":
        logger.info("Initializing Batch client...")
        self._batch_client = BatchClient(self.settings.batch_settings)
        self._batch_client.__enter__()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if self._batch_client:
            self._batch_client.__exit__(exc_type, exc_val, exc_tb)
            self._batch_client = None

    def _get_batch_client(self) -> BatchClient:
        if not self._batch_client:
            raise BatchTaskRunnerError("Batch client not initialized.")
        return self._batch_client

    def prepare_task_info(
        self,
        dataset_id: str,
        run_id: str,
        job_id: str,
        task_def: TaskDefinition,
        image: str,
        task_tags: Optional[Dict[str, str]],
    ) -> Dict[str, Any]:

        pool_id = get_pool_id(task_tags, self.settings.batch_settings)
        batch_job_id = make_batch_job_id(dataset_id, job_id, run_id, pool_id)

        self._create_job_if_needed(batch_job_id, pool_id)

        return {JOB_ID_KEY: batch_job_id}

    def _create_job_if_needed(self, batch_job_id: str, pool_id: str) -> None:
        batch_client = self._get_batch_client()

        # Lock the job creation so that we don't try to create the same job
        # in parallel. Cache the result so that we don't hit the Batch API
        # across multiple threads unnecessarily.

        with job_locks[batch_job_id]:
            cache_key = f"create_batch_job:{batch_job_id}"
            if cache_key in self.response_cache:
                return
            else:
                existing_job = batch_client.get_job(batch_job_id)
                if not existing_job:
                    if not batch_client.get_pool(pool_id):
                        raise BatchTaskRunnerError(f"Batch pool {pool_id} not found.")

                    batch_job_id = batch_client.add_job(
                        job_id=batch_job_id,
                        pool_id=pool_id,
                        make_unique=False,
                        terminate_on_tasks_complete=False,
                    )
                self.response_cache[cache_key] = True

    def submit_tasks(
        self, prepared_tasks: List[PreparedTaskSubmitMessage]
    ) -> List[Union[SuccessfulTaskSubmitResult, FailedTaskSubmitResult]]:
        batch_client = self._get_batch_client()

        batch_submits: Dict[BatchJobInfo, List[BatchTaskInfo]] = defaultdict(list)

        # Transform the tasks into BatchTasks,
        # grouped by the Azure Batch Job they
        # will be submitted to

        for i, prepared_task in enumerate(prepared_tasks):
            submit_msg = prepared_task.task_submit_message
            # run_id = submit_msg.run_id
            # job_id = submit_msg.job_id
            part_id = submit_msg.partition_id
            task_id = submit_msg.definition.id
            run_msg = prepared_task.task_run_message
            task_input_blob_config = prepared_task.task_input_blob_config
            task_tags = prepared_task.task_data.tags

            task_id_for_batch = create_batch_task_id(part_id, task_id)

            pool_id = get_pool_id(task_tags, self.settings.batch_settings)

            # streaming jobs can use ServicePrincipals to load inputs.
            # Batch tasks use SAS tokens.
            assert task_input_blob_config.sas_token is not None

            command = [
                "pctasks",
                "task",
                "run",
                task_input_blob_config.uri,
                "--sas-token",
                task_input_blob_config.sas_token,
            ]

            if task_input_blob_config.account_url:
                command.extend(["--account-url", task_input_blob_config.account_url])

            batch_job_id = prepared_task.task_data.runner_info[JOB_ID_KEY]

            batch_task_id = make_valid_batch_id(task_id_for_batch)

            batch_task = BatchTask(
                task_id=batch_task_id,
                command=command,
                image=run_msg.config.image,
                # Set code directory to working directory,
                # as Azure Batch doesn't allow containers to
                # modify system or user directories.
                environ={"PCTASKS_TASK__CODE_DIR": "./_code"},
            )

            batch_submits[BatchJobInfo(batch_job_id, pool_id)].append(
                BatchTaskInfo(batch_task, i)
            )

        # Create any jobs necessary and submit the tasks

        submit_results: Dict[
            int, Union[SuccessfulTaskSubmitResult, FailedTaskSubmitResult]
        ] = {}

        for batch_job_info, batch_task_infos in batch_submits.items():
            batch_job_id = batch_job_info.job_prefix
            pool_id = batch_job_info.pool_id

            try:
                # Lock to decrease pressure on Azure Batch API
                with job_locks[batch_job_id]:

                    # Submit the tasks
                    task_errors = batch_client.add_collection(
                        batch_job_id,
                        [i.task for i in batch_task_infos],
                    )

                    # Process the results from Azure Batch
                    for i, task_error in enumerate(task_errors):
                        batch_task_info = batch_task_infos[i]
                        task_id = batch_task_info.task.task_id
                        if task_error:
                            err: Any = task_error.message
                            error_msg = err.value
                            submit_results[batch_task_info.index] = (
                                FailedTaskSubmitResult(errors=[error_msg])
                            )
                        else:
                            submit_results[batch_task_info.index] = (
                                SuccessfulTaskSubmitResult(
                                    task_runner_id=BatchTaskId(
                                        batch_job_id=batch_job_id,
                                        batch_task_id=task_id,
                                    ).dict(),
                                )
                            )

            except Exception as e:
                logger.exception(e)

                for batch_task_info in batch_task_infos:
                    submit_results[batch_task_info.index] = FailedTaskSubmitResult(
                        errors=[str(e)]
                    )

        return [submit_results[i] for i in sorted(submit_results)]

    def get_failed_tasks(
        self,
        runner_ids: Dict[str, Dict[str, Dict[str, Any]]],
    ) -> Dict[str, Dict[str, str]]:
        result: Dict[str, Dict[str, str]] = defaultdict(dict)

        for job_id, task_ids in groupby(
            [
                (BatchTaskId.model_validate(batch_id), (partition_id, task_id))
                for partition_id, task_map in runner_ids.items()
                for task_id, batch_id in task_map.items()
            ],
            lambda x: x[0].batch_job_id,
        ):
            indexed_task_ids = {
                batch_id.batch_task_id: (partition_id, task_id)
                for batch_id, (partition_id, task_id) in task_ids
            }

            failed_tasks, job_failed = self._get_failed_tasks(job_id)
            if job_failed:
                for batch_task_id, (partition_id, task_id) in indexed_task_ids.items():
                    if batch_task_id in failed_tasks:
                        result[partition_id][task_id] = failed_tasks[batch_task_id]
                    else:
                        result[partition_id][task_id] = "Job failed"
            else:
                for batch_task_id, error_message in failed_tasks.items():
                    if batch_task_id in indexed_task_ids:
                        partition_id, task_id = indexed_task_ids[batch_task_id]
                        result[partition_id][task_id] = error_message

        return result

    def _get_failed_tasks(self, job_id: str) -> Tuple[Dict[str, str], bool]:
        """Checks for failed tasks in a Job.

        Returns a dictionary of task IDs to error messages for specific task failures.
        Returns True in the second value if the job failed.
        """
        # Check for cached task statuses
        with failed_task_lock:
            cache_key = f"failed_tasks:{job_id}"
            if cache_key in self.response_cache:
                return self.response_cache[cache_key]
            else:
                batch_client = self._get_batch_client()

                job_failed = False

                try:
                    job_info = batch_client.get_job_info(job_id)
                    job_failed = job_info.state == BatchJobState.FAILED
                except HttpResponseError as e:
                    error = e.error  # Avoid type hinting error
                    if error and error.code == "JobNotFound":
                        job_failed = True
                    else:
                        logger.exception(
                            f"(BATCH) Error getting job info for {job_id}."
                        )

                logger.info(
                    "(BATCH) Polling task runner for "
                    f"failed tasks in job {job_id}..."
                )
                try:
                    failed_tasks = batch_client.get_failed_tasks(job_id)
                except Exception:
                    logger.exception("(BATCH) Error getting failed tasks.")
                    # Don't let a Batch API error fail the job;
                    # consider it as "no reported failures"
                    failed_tasks = {}

                total_failed = [len(failed_tasks)]
                if total_failed:
                    logger.info(f"(BATCH)  - {sum(total_failed)} failed tasks found.")
                else:
                    logger.info("(BATCH)  - No failed tasks found.")

                result = (failed_tasks, job_failed)
                self.response_cache[cache_key] = result
                return result

    def poll_task(
        self,
        runner_id: Dict[str, Any],
        previous_poll_count: int,
    ) -> TaskPollResult:
        batch_client = self._get_batch_client()

        task_id = BatchTaskId.model_validate(runner_id)

        task_status_result = batch_client.get_task_status(
            job_id=task_id.batch_job_id, task_id=task_id.batch_task_id
        )

        if task_status_result is None:
            if previous_poll_count < MAX_MISSING_POLLS:
                return TaskPollResult(task_status=TaskRunStatus.PENDING)
            else:
                return TaskPollResult(
                    task_status=TaskRunStatus.FAILED,
                    poll_errors=[
                        f"Batch task not found after {previous_poll_count} polls."
                    ],
                )
        else:
            task_status, error_message = task_status_result
            return TaskPollResult(
                task_status=task_status,
                poll_errors=map_opt(lambda e: [e], error_message),
            )

    def cancel_task(self, runner_id: Dict[str, Any]) -> None:
        batch_client = self._get_batch_client()

        task_id = BatchTaskId.model_validate(runner_id)

        batch_client.terminate_task(
            job_id=task_id.batch_job_id, task_id=task_id.batch_task_id
        )

    def cleanup(self, task_infos: List[Dict[str, Any]]) -> None:
        batch_client = self._get_batch_client()

        job_ids: Set[str] = set()
        for info in task_infos:
            job_ids.add(info[JOB_ID_KEY])
        if job_ids:
            for job_id in job_ids:
                batch_client.terminate_job(job_id=job_id)
