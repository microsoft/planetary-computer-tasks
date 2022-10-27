import logging
from collections import defaultdict
from dataclasses import dataclass
from itertools import groupby
from threading import Lock
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from pctasks.core.models.run import TaskRunStatus
from pctasks.core.models.task import TaskDefinition
from pctasks.core.utils import map_opt
from pctasks.run.batch.client import BatchClient
from pctasks.run.batch.model import BatchTaskId
from pctasks.run.batch.task import BatchTask
from pctasks.run.batch.utils import make_valid_batch_id
from pctasks.run.constants import MAX_MISSING_POLLS
from pctasks.run.models import (
    FailedTaskSubmitResult,
    PreparedTaskSubmitMessage,
    SuccessfulTaskSubmitResult,
    TaskPollResult,
)
from pctasks.run.settings import BatchSettings
from pctasks.run.task.base import TaskRunner

logger = logging.getLogger(__name__)

BATCH_POOL_ID_TAG = "batch_pool_id"

JOB_ID_KEY = "job_id"


class BatchTaskRunnerError(Exception):
    pass


job_locks: Dict[str, Lock] = defaultdict(Lock)


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
        with BatchClient(self.settings.batch_settings) as batch_client:
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
        return {JOB_ID_KEY: batch_job_id}

    def submit_tasks(
        self, prepared_tasks: List[PreparedTaskSubmitMessage]
    ) -> List[Union[SuccessfulTaskSubmitResult, FailedTaskSubmitResult]]:

        batch_submits: Dict[BatchJobInfo, List[BatchTaskInfo]] = defaultdict(list)

        with BatchClient(self.settings.batch_settings) as batch_client:

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

                command = [
                    "pctasks",
                    "task",
                    "run",
                    task_input_blob_config.uri,
                    "--sas-token",
                    task_input_blob_config.sas_token,
                ]

                if task_input_blob_config.account_url:
                    command.extend(
                        ["--account-url", task_input_blob_config.account_url]
                    )

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
                                submit_results[
                                    batch_task_info.index
                                ] = FailedTaskSubmitResult(errors=[error_msg])
                            else:
                                submit_results[
                                    batch_task_info.index
                                ] = SuccessfulTaskSubmitResult(
                                    task_runner_id=BatchTaskId(
                                        batch_job_id=batch_job_id,
                                        batch_task_id=task_id,
                                    ).dict(),
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
    ) -> Dict[str, Set[str]]:
        result: Dict[str, Set[str]] = defaultdict(set)
        for job_id, task_ids in groupby(
            [
                (BatchTaskId.parse_obj(batch_id), (partition_id, task_id))
                for partition_id, task_map in runner_ids.items()
                for task_id, batch_id in task_map.items()
            ],
            lambda x: x[0].batch_job_id,
        ):
            indexed_task_ids: Dict[str, Tuple[str, str]] = {
                batch_id.batch_task_id: (partition_id, task_id)
                for batch_id, (partition_id, task_id) in task_ids
            }
            with BatchClient(self.settings.batch_settings) as batch_client:
                for batch_task_id in batch_client.get_failed_tasks(job_id):
                    partition_id, task_id = indexed_task_ids[batch_task_id]
                    result[partition_id].add(task_id)

        return result

    def poll_task(
        self,
        runner_id: Dict[str, Any],
        previous_poll_count: int,
    ) -> TaskPollResult:
        task_id = BatchTaskId.parse_obj(runner_id)
        with BatchClient(self.settings.batch_settings) as batch_client:
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
        task_id = BatchTaskId.parse_obj(runner_id)
        with BatchClient(self.settings.batch_settings) as batch_client:
            batch_client.terminate_task(
                job_id=task_id.batch_job_id, task_id=task_id.batch_task_id
            )

    def cleanup(self, task_infos: List[Dict[str, Any]]) -> None:
        job_ids = set()
        for info in task_infos:
            job_ids.add(info[JOB_ID_KEY])
        if job_ids:
            with BatchClient(self.settings.batch_settings) as batch_client:
                for job_id in job_ids:
                    batch_client.terminate_job(job_id=job_id)
