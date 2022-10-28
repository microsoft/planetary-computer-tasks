import logging
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple, cast

import azure.batch.batch_auth as batchauth
import azure.batch.models as batchmodels
import dateutil.parser
import msrest.exceptions
import requests.exceptions
import urllib3.exceptions
from azure.batch import BatchServiceClient
from azure.batch.custom.custom_errors import CreateTasksErrorException
from dateutil.tz import tzutc
from requests import Response

from pctasks.core.models.run import TaskRunStatus
from pctasks.core.utils import map_opt
from pctasks.core.utils.backoff import is_common_throttle_exception, with_backoff
from pctasks.run.batch.model import BatchJobInfo
from pctasks.run.batch.task import BatchTask
from pctasks.run.batch.utils import make_unique_job_id
from pctasks.run.settings import BatchSettings

logger = logging.getLogger(__name__)


def cloud_task_to_add_task(
    cloud_task: batchmodels.CloudTask,
) -> batchmodels.TaskAddParameter:
    return batchmodels.TaskAddParameter(
        id=cloud_task.id,
        command_line=cloud_task.command_line,
        container_settings=cloud_task.container_settings,
    )


class BatchClientError(Exception):
    pass


class BatchClient:
    """
    Wrapper around Azure SDK batch client.
    """

    _dry_run: bool = False

    def _with_backoff(self, func: Callable[[], Any]) -> Any:
        def _is_throttle(e: Exception) -> bool:
            if isinstance(e, batchmodels.BatchErrorException):
                error: Any = e.error  # Avoid type hinting error
                if error.code == "OperationTimedOut":
                    return True
            return is_common_throttle_exception(e)

        return with_backoff(func, is_throttle=_is_throttle)

    @classmethod
    def set_dry_run(cls, v: bool) -> None:
        """If set to True, don't submit anything - log information
        about what would have been run.

        Note: BatchJob handles dry_run of submission
        """
        cls._dry_run = v

    def __init__(self, settings: BatchSettings):
        self.settings = settings
        self._client: Optional[BatchServiceClient] = None

        self.credentials = batchauth.SharedKeyCredentials(
            self.settings.get_batch_name(), self.settings.key
        )

    def __enter__(self) -> "BatchClient":
        self._client = BatchServiceClient(self.credentials, batch_url=self.settings.url)
        return self

    def __exit__(self, *args: Any) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None

    def _ensure_client(self) -> BatchServiceClient:
        if not self._client:
            raise BatchClientError(
                "BatchClient not initialized. Use as a context manager."
            )
        return self._client

    def find_active_job(self, prefix: str) -> Optional[str]:
        """Find a running job with the given prefix in the ID

        Returns the ID if found, or None if no running job is found.
        If multiple are found, returns the latest job.
        """
        client = self._ensure_client()
        jobs: List[batchmodels.CloudJob] = list(
            client.job.list(
                job_list_options=batchmodels.JobListOptions(filter="state eq 'active'")
            )
        )

        filtered_jobs: List[batchmodels.CloudJob] = [
            job for job in jobs if cast(str, job.id).startswith(prefix)
        ]

        result: Optional[batchmodels.CloudJob] = next(
            iter(
                sorted(
                    filtered_jobs,
                    key=lambda j: cast(
                        str, cast(batchmodels.CloudJob, j).creation_time
                    ),
                    reverse=True,
                )
            ),
            None,
        )

        def _mo(j: batchmodels.CloudJob) -> str:
            return cast(str, j.id)

        return map_opt(_mo, result)

    def get_job(self, job_id: str) -> Optional[batchmodels.CloudJob]:
        client = self._ensure_client()
        try:
            return cast(
                batchmodels.CloudJob,
                self._with_backoff(lambda: client.job.get(job_id=job_id)),
            )
        except batchmodels.BatchErrorException as e:
            error: Any = e.error  # Avoid type hinting error
            if error.code == "JobNotFound":
                return None
            else:
                raise BatchClientError(error.message.value) from e

    def list_jobs(self, job_id_prefix: str) -> List[batchmodels.CloudJob]:
        client = self._ensure_client()
        try:
            return cast(
                List[batchmodels.CloudJob],
                self._with_backoff(
                    lambda: list(
                        client.job.list(
                            job_list_options=batchmodels.JobListOptions(
                                filter=f"startswith(id, '{job_id_prefix}')"
                            )
                        )
                    )
                ),
            )
        except batchmodels.BatchErrorException as e:
            error: Any = e.error  # Avoid type hinting error
            raise BatchClientError(error.message.value) from e

    def add_job(
        self,
        job_id: str,
        pool_id: Optional[str] = None,
        make_unique: bool = False,
        max_retry_count: int = 0,
        terminate_on_tasks_complete: bool = True,
    ) -> str:
        client = self._ensure_client()

        pool_id = pool_id or self.settings.default_pool_id

        if make_unique:
            job_id = make_unique_job_id(job_id)

        # Ensure ID is less than or equal to 64 characters
        job_id = job_id[:64]

        pool_info = batchmodels.PoolInformation(pool_id=pool_id)

        on_all_tasks_complete = batchmodels.OnAllTasksComplete.terminate_job
        if not terminate_on_tasks_complete:
            on_all_tasks_complete = batchmodels.OnAllTasksComplete.no_action

        job_param = batchmodels.JobAddParameter(
            id=job_id,
            pool_info=pool_info,
            on_all_tasks_complete=on_all_tasks_complete,
            constraints=batchmodels.JobConstraints(
                max_task_retry_count=max_retry_count
            ),
        )
        logger.info(f"(BATCH CLIENT) Adding BatchJob {job_id}")
        self._with_backoff(lambda: client.job.add(job_param))
        return job_id

    def add_task(self, job_id: str, task: BatchTask) -> None:
        client = self._ensure_client()
        task_params = task.to_params()
        logger.info(f"Adding BatchTask {task.task_id}")
        self._with_backoff(lambda: client.task.add(job_id=job_id, task=task_params))

    def add_collection(
        self, job_id: str, tasks: Iterable[BatchTask]
    ) -> List[Optional[batchmodels.BatchError]]:
        """Adds a collection of BatchTasks to the Batch job.

        Returns an optional list of errors corresponding to each task.
        If no error occurred for a task, the list entry will be None.
        """
        client = self._ensure_client()
        params = [task.to_params() for task in tasks]
        try:
            result: batchmodels.TaskAddCollectionResult = self._with_backoff(
                lambda: cast(
                    batchmodels.TaskAddCollectionResult,
                    client.task.add_collection(
                        job_id=job_id,
                        value=params,
                        threads=self.settings.submit_threads,
                    ),
                )
            )
            task_results: List[batchmodels.TaskAddResult] = result.value  # type: ignore
        except CreateTasksErrorException as e:
            logger.warn("Failed to add tasks...")
            for exc in e.errors:
                logger.warn(" -- RETURNED EXCEPTION --")
                logger.exception(exc)
            for failure_task in e.failure_tasks:
                task_add_result = cast(batchmodels.TaskAddResult, failure_task)
                error = cast(batchmodels.BatchError, task_add_result.error)
                if error:
                    logger.error(
                        f"Task {task_add_result.task_id} failed with error: "
                        f"{error.message}"
                    )
                    error_details = cast(batchmodels.BatchError, error).values
                    if error_details:
                        for detail in error_details:
                            logger.error(f"  - {detail.key}: {detail.value}")
            raise
        return [r.error for r in task_results]

    def get_job_info(self, job_id: str) -> BatchJobInfo:
        client = self._ensure_client()
        cloud_job = self._with_backoff(
            lambda: cast(batchmodels.CloudJob, client.job.get(job_id=job_id))
        )
        tasks: List[batchmodels.CloudTask] = list(client.task.list(job_id))
        return BatchJobInfo.from_batch(cloud_job=cloud_job, tasks=tasks)

    def resubmit_failed_tasks(
        self,
        job_id: str,
        retry_job_id: Optional[str] = None,
        max_retry_count: int = 2,
    ) -> None:
        client = self._ensure_client()

        tasks = list(client.task.list(job_id))
        failed_tasks = [
            cast(batchmodels.CloudTask, task)
            for task in tasks
            if task.execution_info.result == "failure"
        ]
        logger.info(f"Found {len(failed_tasks)} failed tasks...")

        # If this job is complete, create a new one.
        # If not, just reactivate
        job = cast(batchmodels.CloudJob, client.job.get(job_id=job_id))

        if job.state == batchmodels.JobState.completed:
            logger.info("Job already completed. Creating retry job...")
            task_adds = [cloud_task_to_add_task(task) for task in failed_tasks]

            make_unique = False
            if retry_job_id is None:
                retry_job_id = f"{job_id}-retry"
                make_unique = True

            updated_job_id = self.add_job(
                retry_job_id, make_unique=make_unique, max_retry_count=max_retry_count
            )

            logger.info(f"  -- Created job {retry_job_id}")

            client.task.add_collection(
                job_id=updated_job_id,
                value=task_adds,
                threads=self.settings.submit_threads,
            )

            logger.info(f"  -- Added {len(failed_tasks)} tasks.")

        else:
            logger.info("Reactivating tasks...")
            for task in failed_tasks:
                client.task.reactivate(job_id=job_id, task_id=task.id)

    def restart_hanging_tasks(self, job_id: str, max_runtime: timedelta) -> None:
        client = self._ensure_client()

        tasks = list(client.task.list(job_id))
        print(len(tasks))
        running_tasks = [
            cast(batchmodels.CloudTask, task)
            for task in tasks
            if task.state == "running"
        ]
        logger.info(f"Found {len(running_tasks)} running tasks...")

        hanging_tasks: List[batchmodels.CloudTask] = []

        for task in running_tasks:
            exec_info = cast(batchmodels.TaskExecutionInformation, task.execution_info)
            start_time = cast(datetime, exec_info.start_time)
            run_time = datetime.utcnow() - start_time.replace(tzinfo=None)
            if run_time > max_runtime:
                hanging_tasks.append(task)
                if self._dry_run:
                    print(f"{task.id} - {run_time}")

        logger.info(f"Found {len(hanging_tasks)} hanging tasks")
        if self._dry_run:
            logger.info("[DRY RUN] - Skipping restart")
        elif len(hanging_tasks) > 0:
            logger.info("Restarting...")

            for task in hanging_tasks:
                print(f" - Terminating {task.id}")
                client.task.terminate(job_id=job_id, task_id=task.id)
                print(f" -- Reactivating {task.id}")
                client.task.reactivate(job_id=job_id, task_id=task.id)

    def restart_silent_tasks(
        self,
        job_id: str,
        max_since_log_output: timedelta,
        task_filter: Optional[Callable[[batchmodels.CloudTask], bool]] = None,
    ) -> None:
        client = self._ensure_client()

        tasks = list(client.task.list(job_id))
        running_tasks = [
            cast(batchmodels.CloudTask, task)
            for task in tasks
            if task.state == "running"
        ]
        logger.info(f"Found {len(running_tasks)} running tasks...")

        if task_filter:
            running_tasks = [task for task in running_tasks if task_filter(task)]

        hanging_tasks: List[batchmodels.CloudTask] = []

        for task in running_tasks:
            r: Optional[Response] = None
            try:
                raw_resp = client.file.get_properties_from_task(
                    job_id=job_id, task_id=task.id, file_path="stdout.txt", raw=True
                )
                assert raw_resp
                r = cast(Response, raw_resp.response)
                r.raise_for_status()

                # stdout.txt exists
                # Check if it's been modified within the
                # time limit.

                last_modified_time = dateutil.parser.parse(r.headers["Last-Modified"])
                now = datetime.now(tzutc())
                last_modified = now - last_modified_time

                if last_modified > max_since_log_output:
                    hanging_tasks.append(task)
                    if self._dry_run:
                        print(f"{task.id} - {last_modified}")

            except (batchmodels.BatchErrorException):

                # stdout.txt doesn't exist
                # Check if it's been running without output for
                # the max time.

                exec_info = cast(
                    batchmodels.TaskExecutionInformation, task.execution_info
                )
                start_time = cast(datetime, exec_info.start_time)
                run_time = datetime.utcnow() - start_time.replace(tzinfo=None)

                if run_time > max_since_log_output:
                    hanging_tasks.append(task)
                    if self._dry_run:
                        print(f"{task.id} - {run_time}")

            except (
                msrest.exceptions.ClientRequestError,
                requests.exceptions.RetryError,
                urllib3.exceptions.MaxRetryError,
            ):
                # Sometimes querying the node can be unresponsive.
                # Don't consider this a hanging task as this
                # is potentially an issue with the node or throttling
                # of Batch requests; once
                # a more precise reason for these exceptions
                # is determined we should handle these appropriately.

                logger.warn(f"Task {task.id} is unresponsive!")

        logger.info(f"Found {len(hanging_tasks)} hanging tasks")
        if self._dry_run:
            logger.info("[DRY RUN] - Skipping restart")
        elif len(hanging_tasks) > 0:
            logger.info("Restarting...")

            for task in hanging_tasks:
                print(f" - Terminating {task.id}")
                client.task.terminate(job_id=job_id, task_id=task.id)
                print(f" -- Reactivating {task.id}")
                client.task.reactivate(job_id=job_id, task_id=task.id)

    def get_task_status(
        self, job_id: str, task_id: str
    ) -> Optional[Tuple[TaskRunStatus, Optional[str]]]:
        """Returns the status of a task.

        If the task isn't found, returns None.
        If the is errored, will try to return the error message in
        the second tuple element.
        Otherwise, returns the status as the first tuple element.
        """
        client = self._ensure_client()

        try:
            task = cast(
                batchmodels.CloudTask,
                client.task.get(job_id=job_id, task_id=task_id),
            )
        except batchmodels.BatchErrorException as e:
            error: Any = e.error  # Avoid type hinting error
            if error.code == "TaskNotFound":
                return None
            if error.code == "JobNotFound":
                return None
            else:
                raise BatchClientError(error.message.value)

        logger.debug(f"BATCH TASK STATUS: {task.state}")

        task_state = cast(batchmodels.TaskState, task.state)
        execution_info = cast(batchmodels.TaskExecutionInformation, task.execution_info)
        if task_state == batchmodels.TaskState.completed:
            if execution_info.exit_code != 0:
                return (
                    TaskRunStatus.FAILED,
                    execution_info.failure_info.message
                    if execution_info.failure_info
                    else None,
                )
            else:
                return (TaskRunStatus.COMPLETED, None)
        if task_state == batchmodels.TaskState.active:
            return (TaskRunStatus.PENDING, None)
        if task_state == batchmodels.TaskState.preparing:
            return (TaskRunStatus.STARTING, None)
        if task_state == batchmodels.TaskState.running:
            return (TaskRunStatus.RUNNING, None)

        if task_state == batchmodels.TaskState.running:
            return (TaskRunStatus.RUNNING, None)
        else:
            return (TaskRunStatus.SUBMITTED, None)

    def get_failed_tasks(self, job_id: str) -> Dict[str, str]:
        client = self._ensure_client()
        completed_tasks = client.task.list(
            job_id,
            task_list_options=batchmodels.TaskListOptions(
                filter="state eq 'completed'"
            ),
        )
        result: Dict[str, str] = {}
        for task in completed_tasks:
            t = cast(batchmodels.CloudTask, task)
            execution_info = cast(
                batchmodels.TaskExecutionInformation,
                t.execution_info,
            )
            if execution_info.result == batchmodels.TaskExecutionResult.failure:
                if execution_info.failure_info and execution_info.failure_info.message:
                    result[t.id] = execution_info.failure_info.message
                else:
                    result[t.id] = "Azure Batch task failed without error message"

        return result

    def get_pool(self, pool_id: str) -> Optional[batchmodels.PoolInformation]:
        client = self._ensure_client()

        try:
            return cast(
                batchmodels.PoolInformation,
                self._with_backoff(lambda: client.pool.get(pool_id)),
            )
        except batchmodels.BatchErrorException as e:
            error: Any = e.error  # Avoid type hinting error
            if error.code == "PoolNotFound":
                return None
            else:
                raise BatchClientError(error.message.value)

    def terminate_job(self, job_id: str) -> None:
        client = self._ensure_client()

        def _terminate() -> None:
            try:
                client.job.terminate(job_id=job_id)
            except batchmodels.BatchErrorException as e:
                error: Any = e.error  # Avoid type hinting error
                if error.code == "JobNotFound":
                    logger.warning(f"Job {job_id} not found - skipping termination")
                    return
                if error.code == "JobTerminating":
                    return
                if error.code == "JobCompleted":
                    return

        self._with_backoff(_terminate)

    def terminate_task(self, job_id: str, task_id: str) -> None:
        client = self._ensure_client()

        self._with_backoff(
            lambda: client.task.terminate(job_id=job_id, task_id=task_id)
        )
