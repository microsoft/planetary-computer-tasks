import logging
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple, cast

import azure.batch.models as batchmodels
import requests.exceptions
import urllib3.exceptions
from azure.batch import BatchClient as AzureBatchClient

# from azure.batch.custom.custom_errors import CreateTasksErrorException
from azure.batch.models import (
    BatchError,
    BatchErrorDetail,
    BatchErrorMessage,
    BatchJob,
    BatchJobConstraints,
    BatchJobCreateContent,
    BatchPoolInfo,
    OnAllBatchTasksComplete,
)
from azure.core.exceptions import HttpResponseError
from dateutil.tz import tzutc
from requests import Response

from pctasks.core.models.run import TaskRunStatus
from pctasks.core.utils import map_opt
from pctasks.core.utils.backoff import is_common_throttle_exception, with_backoff
from pctasks.core.utils.credential import get_credential
from pctasks.run.batch.model import BatchJobInfo
from pctasks.run.batch.task import BatchTask
from pctasks.run.batch.utils import make_unique_job_id
from pctasks.run.settings import BatchSettings

logger = logging.getLogger(__name__)


def cloud_task_to_add_task(
    cloud_task: batchmodels.BatchTask,
) -> batchmodels.BatchTaskCreateContent:
    return batchmodels.BatchTaskCreateContent(
        id=cloud_task.id,  # type: ignore
        command_line=cloud_task.command_line,  # type: ignore
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
            if isinstance(e, BatchError):
                error: Any = e.message  # Avoid type hinting error
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
        self._client: Optional[AzureBatchClient] = None

        self.credentials = get_credential()

    def __enter__(self) -> "BatchClient":
        self._client = AzureBatchClient(
            endpoint=self.settings.url, credential=self.credentials
        )
        return self

    def __exit__(self, *args: Any) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None

    def _ensure_client(self) -> AzureBatchClient:
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
        jobs = list(client.list_jobs(filter="state eq 'active'"))

        filtered_jobs = [job for job in jobs if cast(str, job.id).startswith(prefix)]

        result = next(
            iter(
                sorted(
                    filtered_jobs,
                    key=lambda j: cast(str, j.creation_time),
                    reverse=True,
                )
            ),
            None,
        )

        def _mo(j: BatchJob) -> str:
            return cast(str, j.id)

        return map_opt(_mo, result)

    def _to_batch_error(self, error: Exception) -> BatchError:
        """
        Convert any exception to BatchError format.

        :param error: Any exception that needs to be converted to BatchError
        :type error: Exception
        :return: A BatchError representation of the exception
        :rtype: ~azure.batch.models.BatchError
        :raises AttributeError: If the ErrorMessage object cannot be properly created

        Example:

        ```python
        try:
            # Some batch operation
        except Exception as e:
            batch_error = _to_batch_error(e)
            logger.error(f"Operation failed: {batch_error.message}")
        ```
        """

        code: str = getattr(error, "code", type(error).__name__)

        if hasattr(error, "message"):
            message = error.message  # type: ignore
        else:
            message = str(error)

        if isinstance(message, batchmodels.BatchErrorMessage):
            error_message = message
        else:
            error_message = BatchErrorMessage(value=message)

        values: List[BatchErrorDetail] = []
        return BatchError(code=code, message=error_message, values_property=values)

    def get_job(self, job_id: str) -> Optional[BatchJob]:
        client = self._ensure_client()
        try:
            return cast(
                BatchJob,
                self._with_backoff(lambda: client.get_job(job_id=job_id)),
            )
        except HttpResponseError as e:
            if error := e.error:
                if error.code == "JobNotFound":
                    return None
            else:
                raise BatchClientError(e.message) from e
        return None

    def list_jobs(self, job_id_prefix: str) -> List[BatchJob]:
        client = self._ensure_client()
        try:
            return cast(
                List[BatchJob],
                self._with_backoff(
                    lambda: list(
                        client.list_jobs(filter=f"startswith(id, '{job_id_prefix}')")
                    )
                ),
            )
        except HttpResponseError as e:
            raise BatchClientError(e.message) from e

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

        pool_info = BatchPoolInfo(pool_id=pool_id)

        on_all_tasks_complete = OnAllBatchTasksComplete.TERMINATE_JOB
        if not terminate_on_tasks_complete:
            on_all_tasks_complete = OnAllBatchTasksComplete.NO_ACTION

        job_param = BatchJobCreateContent(
            id=job_id,
            pool_info=pool_info,
            on_all_tasks_complete=on_all_tasks_complete,
            constraints=BatchJobConstraints(max_task_retry_count=max_retry_count),
        )
        logger.info(f"(BATCH CLIENT) Adding BatchJob {job_id}")
        self._with_backoff(lambda: client.create_job(job_param))
        return job_id

    def add_task(self, job_id: str, task: BatchTask) -> None:
        client = self._ensure_client()
        task_params = task.to_params()
        logger.info(f"Adding BatchTask {task.task_id}")
        self._with_backoff(lambda: client.create_task(job_id=job_id, task=task_params))

    def add_collection(
        self, job_id: str, tasks: Iterable[BatchTask]
    ) -> List[Optional[batchmodels.BatchError]]:
        """Adds a collection of BatchTasks to the Batch job.

        Returns an optional list of errors corresponding to each task.
        If no error occurred for a task, the list entry will be None.
        """
        client = self._ensure_client()
        params = [task.to_params() for task in tasks]
        _tasks = batchmodels.BatchTaskGroup(value=params)
        try:
            result: batchmodels.BatchTaskAddCollectionResult = self._with_backoff(
                lambda: client.create_task_collection(
                    job_id=job_id,
                    task_collection=_tasks,
                )
            )
            task_results: List[batchmodels.TaskAddResult] = result.value  # type: ignore
        except HttpResponseError as e:
            logger.error("Failed to add tasks...")

            # # for exc in e.error:
            # #     exc = cast(Exception, exc)
            # #     logger.error(" -- RETURNED EXCEPTION --")
            # #     logger.error(exc)

            # for task_add_result in e.failure_tasks:
            #     task_add_result = cast(batchmodels.TaskAddResult, task_add_result)

            #     if task_add_result.error is None:
            #         continue

            #     batch_error = self._to_batch_error(task_add_result.error)
            #     logger.error(
            #         f"Failed to create task {task_add_result.task_id} with error: {batch_error.message.value}"  # noqa: E501
            #     )

            #     if batch_error.values:
            #         for detail in batch_error.values:
            #             logger.error(f"  - {detail.key}: {detail.value}")
            raise
        return [r.error for r in task_results]

    def get_job_info(self, job_id: str) -> BatchJobInfo:
        client = self._ensure_client()
        cloud_job = self._with_backoff(
            lambda: cast(BatchJob, client.get_job(job_id=job_id))
        )
        tasks: List[batchmodels.BatchTask] = list(client.list_tasks(job_id))
        return BatchJobInfo.from_batch(cloud_job=cloud_job, tasks=tasks)

    def resubmit_failed_tasks(
        self,
        job_id: str,
        retry_job_id: Optional[str] = None,
        max_retry_count: int = 2,
    ) -> None:
        client = self._ensure_client()

        tasks = list(client.list_tasks(job_id))
        failed_tasks = [
            cast(batchmodels.BatchTask, task)
            for task in tasks
            if task.execution_info.result == "failure"  # type: ignore
        ]
        logger.info(f"Found {len(failed_tasks)} failed tasks...")

        # If this job is complete, create a new one.
        # If not, just reactivate
        job = client.get_job(job_id=job_id)

        if job.state == batchmodels.BatchJobState.COMPLETED:
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

            client.create_task_collection(
                job_id=updated_job_id,
                task_collection=batchmodels.BatchTaskGroup(value=task_adds),
            )

            logger.info(f"  -- Added {len(failed_tasks)} tasks.")

        else:
            logger.info("Reactivating tasks...")
            for task in failed_tasks:
                client.reactivate_task(job_id=job_id, task_id=task.id)  # type: ignore

    def restart_hanging_tasks(self, job_id: str, max_runtime: timedelta) -> None:
        client = self._ensure_client()

        tasks = list(client.list_tasks(job_id))

        running_tasks = [
            task for task in tasks if task.state == batchmodels.BatchTaskState.RUNNING
        ]
        logger.info(f"Found {len(running_tasks)} running tasks...")

        hanging_tasks: list[batchmodels.BatchTask] = []

        for task in running_tasks:
            if exec_info := task.execution_info:
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
                if task_id := task.id:
                    print(f" - Terminating {task_id}")
                    client.terminate_task(job_id=job_id, task_id=task_id)
                    print(f" -- Reactivating {task_id}")
                    client.reactivate_task(job_id=job_id, task_id=task_id)

    def restart_silent_tasks(
        self,
        job_id: str,
        max_since_log_output: timedelta,
        task_filter: Optional[Callable[[batchmodels.BatchTask], bool]] = None,
    ) -> None:
        client = self._ensure_client()

        tasks = list(client.list_tasks(job_id))
        running_tasks = [
            task for task in tasks if task.state == batchmodels.BatchTaskState.RUNNING
        ]
        logger.info(f"Found {len(running_tasks)} running tasks...")

        if task_filter:
            running_tasks = [task for task in running_tasks if task_filter(task)]

        hanging_tasks = []

        for task in running_tasks:
            r: Optional[Response] = None
            try:
                raw_resp = client.get_task_file_properties(
                    job_id=job_id, task_id=task.id, file_path="stdout.txt"  # type: ignore
                )

                # stdout.txt exists
                # Check if it's been modified within the
                # time limit.

                last_modified_time = raw_resp.last_modified
                now = datetime.now(tzutc())
                last_modified = now - last_modified_time

                if last_modified > max_since_log_output:
                    hanging_tasks.append(task)
                    if self._dry_run:
                        print(f"{task.id} - {last_modified}")

            except HttpResponseError as e:
                # stdout.txt doesn't exist
                # Check if it's been running without output for
                # the max time.

                exec_info = task.execution_info
                start_time = exec_info.start_time  # type: ignore
                run_time = datetime.utcnow() - start_time.replace(tzinfo=None)  # type: ignore

                if run_time > max_since_log_output:
                    hanging_tasks.append(task)
                    if self._dry_run:
                        print(f"{task.id} - {run_time}")

            except (
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
                if task_id := task.id:
                    print(f" - Terminating {task_id}")
                    client.terminate_task(job_id=job_id, task_id=task_id)
                    print(f" -- Reactivating {task_id}")
                    client.reactivate_task(job_id=job_id, task_id=task_id)

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
            task = client.get_task(job_id=job_id, task_id=task_id)
        except HttpResponseError as e:
            if error := e.error:
                if error.code == "TaskNotFound":
                    return None
                if error.code == "JobNotFound":
                    return None
            else:
                raise BatchClientError(e.message)

        logger.debug(f"BATCH TASK STATUS: {task.state}")

        task_state = task.state
        execution_info = task.execution_info
        assert execution_info
        if task_state == batchmodels.BatchTaskState.COMPLETED:
            if execution_info.exit_code != 0:
                return (
                    TaskRunStatus.FAILED,
                    (
                        execution_info.failure_info.message
                        if execution_info.failure_info
                        else None
                    ),
                )
            else:
                return (TaskRunStatus.COMPLETED, None)
        if task_state == batchmodels.BatchTaskState.ACTIVE:
            return (TaskRunStatus.PENDING, None)
        if task_state == batchmodels.BatchTaskState.PREPARING:
            return (TaskRunStatus.STARTING, None)
        if task_state == batchmodels.BatchTaskState.RUNNING:
            return (TaskRunStatus.RUNNING, None)

        if task_state == batchmodels.BatchTaskState.RUNNING:
            return (TaskRunStatus.RUNNING, None)
        else:
            return (TaskRunStatus.SUBMITTED, None)

    def get_failed_tasks(self, job_id: str) -> Dict[str, str]:
        client = self._ensure_client()
        completed_tasks = client.list_tasks(job_id, filter="state eq 'completed'")
        result: Dict[str, str] = {}
        for task in completed_tasks:
            if execution_info := task.execution_info:
                if (
                    execution_info.result
                    == batchmodels.BatchTaskExecutionResult.FAILURE
                ):
                    if task_id := task.id:
                        if (
                            execution_info.failure_info
                            and execution_info.failure_info.message
                        ):
                            result[task_id] = execution_info.failure_info.message
                        else:
                            result[task_id] = (
                                "Azure Batch task failed without error message"
                            )

        return result

    def get_pool(self, pool_id: str) -> Optional[batchmodels.BatchPoolInfo]:
        client = self._ensure_client()

        try:
            return cast(
                batchmodels.BatchPoolInfo,
                self._with_backoff(lambda: client.get_pool(pool_id)),
            )
        except HttpResponseError as e:
            if error := e.error:
                if error.code == "PoolNotFound":
                    return None
            else:
                raise BatchClientError(e.message)
        return None

    def terminate_job(self, job_id: str) -> None:
        client = self._ensure_client()

        def _terminate() -> None:
            try:
                client.terminate_job(job_id=job_id)
            except HttpResponseError as e:
                if error := e.error:
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
            lambda: client.terminate_task(job_id=job_id, task_id=task_id)
        )
