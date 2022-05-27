from collections import defaultdict
import logging
from threading import Lock
import re
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import azure.batch.models as batchmodels

from pctasks.core.models.config import BlobConfig
from pctasks.core.models.record import TaskRunStatus
from pctasks.core.models.task import TaskRunMessage
from pctasks.core.utils import map_opt
from pctasks.execute.batch.client import BatchClient
from pctasks.execute.batch.model import BatchTaskId
from pctasks.execute.batch.task import BatchTask
from pctasks.execute.batch.utils import make_unique_job_id, make_valid_batch_id
from pctasks.execute.constants import MAX_MISSING_POLLS
from pctasks.execute.executor.base import TaskExecutor
from pctasks.execute.models import (
    FailedSubmitResult,
    PreparedTaskSubmitMessage,
    SuccessfulSubmitResult,
    TaskPollResult,
    TaskSubmitMessage,
)
from pctasks.execute.settings import BatchSettings, ExecutorSettings

logger = logging.getLogger(__name__)

BATCH_POOL_ID_TAG = "batch_pool_id"


class BatchExecutorError(Exception):
    pass


job_locks: Dict[str, Lock] = defaultdict(Lock)


def get_pool_id(tags: Optional[Dict[str, str]], batch_settings: BatchSettings) -> str:
    return (tags or {}).get(BATCH_POOL_ID_TAG, batch_settings.default_pool_id)


def transfer_index(job_id: str, task_id: str) -> Tuple[str, str]:
    """Transfer an index from a job id to the task id.

    Job IDs can have indexes when created from a
    list through foreach. We want to submit tasks
    for these types of jobs to the same Azure Batch
    job, so remove the index when creating the Azure Batch
    job name, and transfer it to the task id.
    """
    m = re.search(r"\[(\d+)\]", job_id)
    if m:
        result_job_id = re.sub(r"\[\d+\]", "", job_id)
        result_task_id = f"{task_id}_{m.group(1)}"
        return (result_job_id, result_task_id)
    return (job_id, task_id)


class BatchTaskExecutor(TaskExecutor):
    def submit(
        self,
        prepared_tasks: List[PreparedTaskSubmitMessage],
        settings: ExecutorSettings,
    ) -> List[Union[SuccessfulSubmitResult, FailedSubmitResult]]:

        # TODO: Fix this

        job_id, task_id = (
            submit_msg.job_id,
            submit_msg.config.id,
        )

        results: List[Union[SuccessfulSubmitResult, FailedSubmitResult]] = []

        created_jobs: Set[str] = set()

        batch_submits: List[Tuple[str, str]] = []

        with BatchClient(settings.batch_settings) as batch_client:
            for prepared_task in prepared_tasks:
                submit_msg = prepared_task.task_submit_message
                run_msg = prepared_task.task_run_message
                task_input_blob_config = prepared_task.task_input_blob_config
                task_tags = prepared_task.task_tags

                job_id_for_batch, task_id_for_batch = transfer_index(job_id, task_id)

                pool_id = get_pool_id(task_tags, settings.batch_settings)

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

                batch_job_prefix = make_valid_batch_id(
                    f"{submit_msg.dataset}_{job_id_for_batch}_{pool_id}"
                )
                batch_task_id = make_valid_batch_id(task_id_for_batch)

                batch_task = BatchTask(
                    task_id=batch_task_id,
                    command=command,
                    image=run_msg.config.image,
                )

                retry_count = 0
                task_submitted = False
                batch_job_id: Optional[str] = None
                with job_locks[batch_job_prefix]:

                    batch_job_id = batch_client.find_active_job(
                        batch_job_prefix
                    )

                    if not batch_job_id:

                        if batch_job_id in created_jobs:
                            # If it's been previously created but before API acknowledges it,
                            # don't recreate it.

                            if not batch_client.get_pool(pool_id):
                                raise BatchExecutorError(
                                    f"Batch pool {pool_id} not found."
                                )

                            batch_job_id = make_unique_job_id(batch_job_prefix)

                            logger.info(f"Creating batch job {batch_job_id}.")
                            batch_job_id = batch_client.add_job(
                                batch_job_id, pool_id=pool_id, make_unique=False
                            )
                    else:
                        logger.info(f"Found existing batch job {batch_job_id}.")

                if not batch_job_id:
                    raise BatchExecutorError(
                        f"Could not create batch job for {batch_job_prefix}."
                    )

                batch_submits.append((batch_job_id, batch_task))


                while not task_submitted and retry_count <= 1:
                    try:

                    except batchmodels.BatchErrorException as e:
                        error: Any = e.error  # Avoid type hinting error
                        if error.code == "JobCompleted":
                            if retry_count > 1:
                                raise
                            retry_count += 1
                        else:
                            raise

            if not batch_job_id:
                results.append(
                    FailedSubmitResult(errors=["Failed to create batch job."])
                )
            else:
                results.append(
                    SuccessfulSubmitResult(
                        executor_id=BatchTaskId(
                            batch_job_id=batch_job_id, batch_task_id=batch_task_id
                        ).dict(),
                        task_id=task_id,
                    )
                )

        return results

    def poll_task(
        self,
        executor_id: Dict[str, Any],
        previous_poll_count: int,
        settings: ExecutorSettings,
    ) -> TaskPollResult:
        task_id = BatchTaskId.parse_obj(executor_id)
        with BatchClient(settings.batch_settings) as batch_client:
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
