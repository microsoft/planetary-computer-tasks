import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pctasks.core.models.run import TaskRunStatus
from pctasks.core.models.task import (
    CompletedTaskResult,
    FailedTaskResult,
    TaskDefinition,
    TaskResult,
    WaitTaskResult,
)
from pctasks.core.storage.base import Storage
from pctasks.run.models import (
    FailedTaskSubmitResult,
    JobPartitionSubmitMessage,
    PreparedTaskSubmitMessage,
    SuccessfulTaskSubmitResult,
    TaskSubmitMessage,
)
from pctasks.run.settings import RunSettings
from pctasks.run.task.base import TaskRunner
from pctasks.run.task.prepare import prepare_task
from pctasks.run.template import template_args

logger = logging.getLogger(__name__)


class TaskStateStatus(str, Enum):
    """The status of a running task."""

    NEW = "new"
    SUBMITTED = "submitted"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    WAITING = "waiting"
    CANCELLED = "cancelled"

    @property
    def is_active(self) -> bool:
        return self == self.SUBMITTED or self == self.RUNNING

    @classmethod
    def from_task_run_status(cls, status: TaskRunStatus) -> "TaskStateStatus":
        if status == TaskRunStatus.RECEIVED:
            return cls.NEW
        elif status == TaskRunStatus.SUBMITTED:
            return cls.SUBMITTED
        elif status == TaskRunStatus.STARTING:
            return cls.RUNNING
        elif status == TaskRunStatus.RUNNING:
            return cls.RUNNING
        elif status == TaskRunStatus.COMPLETING:
            return cls.RUNNING
        elif status == TaskRunStatus.COMPLETED:
            return cls.COMPLETED
        elif status == TaskRunStatus.FAILED:
            return cls.FAILED
        elif status == TaskRunStatus.WAITING:
            return cls.WAITING
        elif status == TaskRunStatus.CANCELLED:
            return cls.CANCELLED
        else:
            raise ValueError(f"Invalid task status {status}")


class JobPartitionStateStatus(str, Enum):
    NEW = "new"
    NOTASKS = "notasks"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


@dataclass
class WaitInfo:
    start_time: float
    duration: float


@dataclass
class TaskState:
    prepared_task: PreparedTaskSubmitMessage
    """The prepared task. Remains fixed"""
    job_part_run_record_id: str

    _status: TaskStateStatus = TaskStateStatus.NEW
    _submit_result: Optional[
        Union[SuccessfulTaskSubmitResult, FailedTaskSubmitResult]
    ] = None
    _task_result: Optional[TaskResult] = None

    status_updated: bool = False
    """True if task record has been updated to current status"""

    _poll_count = 0
    _last_poll_time: Optional[float] = None
    _last_check_output_time: Optional[float] = None

    # Time that the status blob was last checked
    _last_check_status_time: Optional[float] = None

    _wait_retries: int = 0
    _wait_info: Optional[WaitInfo] = None

    @property
    def status(self) -> TaskStateStatus:
        return self._status

    @property
    def submit_result(
        self,
    ) -> Optional[Union[SuccessfulTaskSubmitResult, FailedTaskSubmitResult]]:
        return self._submit_result

    @property
    def task_result(self) -> Optional[TaskResult]:
        return self._task_result

    @property
    def run_id(self) -> str:
        return self.prepared_task.task_submit_message.run_id

    @property
    def job_id(self) -> str:
        return self.prepared_task.task_submit_message.job_id

    @property
    def task_id(self) -> str:
        return self.prepared_task.task_submit_message.definition.id

    def change_status(self, status: TaskStateStatus) -> bool:
        if not self.status == status:
            self._status = status
            self.status_updated = False
            return True
        return False

    def should_poll(self, wait_duration: float) -> bool:
        if self.status.is_active and (
            self._last_poll_time is None
            or (time.monotonic() - self._last_poll_time) > wait_duration
        ):
            return True
        return False

    def should_check_output(self, wait_duration: float) -> bool:
        if self.status.is_active and (
            self._last_check_output_time is None
            or (time.monotonic() - self._last_check_output_time) > wait_duration
        ):
            return True
        return False

    def should_check_status_blob(self, wait_duration: float) -> bool:
        if self.status.is_active and (
            self._last_check_status_time is None
            or (time.monotonic() - self._last_check_status_time) > wait_duration
        ):
            return True
        return False

    def update_if_waiting(self) -> None:
        """Update state based on waiting status.

        If this task is waiting, check if the wait time has expired.
        If so, set the status back to NEW
        """
        if self.status == TaskStateStatus.WAITING:
            if self._wait_info:
                if (
                    time.monotonic() - self._wait_info.start_time
                    > self._wait_info.duration
                ):
                    self.change_status(TaskStateStatus.NEW)
                    self._submit_result = None
                    self._wait_info = None

    def set_waiting(self, wait_duration: float) -> None:
        self._wait_retries += 1
        self.change_status(TaskStateStatus.WAITING)
        self._wait_info = WaitInfo(start_time=time.monotonic(), duration=wait_duration)
        self._submit_result = None

    def submit(self, executor: TaskRunner) -> None:
        self._wait_info = None
        if self.submit_result:
            raise Exception(
                f"Task {self.prepared_task.task_submit_message.definition.id} "
                "already submitted "
                f"for job {self.job_id}"
            )

        try:
            submit_result = executor.submit_tasks([self.prepared_task])
            self.set_submitted(submit_result[0])
        except Exception as e:
            self.set_submitted(FailedTaskSubmitResult(errors=[str(e)]))

    def set_failed(self, errors: List[str]) -> None:
        self.change_status(TaskStateStatus.FAILED)
        self._task_result = TaskResult.failed(
            errors=errors,
        )

    def set_submitted(
        self, submit_result: Union[SuccessfulTaskSubmitResult, FailedTaskSubmitResult]
    ) -> None:
        self._submit_result = submit_result

        if isinstance(submit_result, SuccessfulTaskSubmitResult):
            self.change_status(TaskStateStatus.SUBMITTED)
        else:
            self.set_failed(submit_result.errors)

    def poll(
        self, executor: TaskRunner, storage: Storage, settings: RunSettings
    ) -> None:
        """Poll the task and modify the state accordingly."""
        if not self.status.is_active:
            return

        self._last_poll_time = time.monotonic()
        if not self.submit_result:
            raise Exception("Can not poll task that has not been submitted.")

        if isinstance(self.submit_result, FailedTaskSubmitResult):
            raise Exception("Can not poll task that was failed to be submitted.")

        try:
            result = executor.poll_task(
                self.submit_result.task_runner_id,
                previous_poll_count=self._poll_count,
            )
            logger.debug(
                f"Polled task {json.dumps(self.submit_result.task_runner_id)}"
                f": {result}"
            )
            self._poll_count += 1

            if result.task_status == TaskRunStatus.FAILED:
                self.set_failed(result.poll_errors or ["Poll showed task as failed."])
            elif result.task_status == TaskRunStatus.CANCELLED:
                self.set_failed(
                    result.poll_errors or ["Poll showed task as cancelled."]
                )
            elif result.task_status == TaskRunStatus.COMPLETED:
                # Check for output one last time
                if not self.process_output_if_available(storage, settings):
                    self.set_failed(
                        errors=[
                            "Poll showed task as completed but no output available."
                        ]
                    )
        except Exception as e:
            logger.exception(e)
            error_lines = str(e).split("\n")

            self.set_failed(
                [
                    (
                        "Failed to poll task "
                        f"{json.dumps(self.submit_result.task_runner_id)}"
                    )
                ]
                + error_lines
            )

    def process_output_if_available(
        self, storage: Storage, settings: RunSettings
    ) -> bool:
        """Checks for task output, indicating completion. Updates state accordingly.

        Returns if output was found.
        """
        self._last_check_output_time = time.monotonic()
        path = storage.get_path(
            self.prepared_task.task_run_message.config.output_blob_config.uri
        )

        if storage.file_exists(path):
            self._task_result = TaskResult.parse_subclass(storage.read_json(path))

            if isinstance(self.task_result, CompletedTaskResult):
                self.change_status(TaskStateStatus.COMPLETED)
            elif isinstance(self.task_result, FailedTaskResult):
                self.set_failed(
                    self.task_result.errors
                    or ["Task failed without errors. Check logs."]
                )
            elif isinstance(self.task_result, WaitTaskResult):
                if self._wait_retries >= settings.max_wait_retries:
                    self.set_failed(
                        [
                            "Task requested to wait more than "
                            f"{settings.max_wait_retries} times."
                        ]
                    )
                else:
                    self.set_waiting(
                        self.task_result.wait_seconds
                        or settings.default_task_wait_seconds
                    )
            return True

        return False

    def process_status_blob_if_available(self, storage: Storage) -> None:
        self._last_check_status_time = time.monotonic()
        path = storage.get_path(
            self.prepared_task.task_run_message.config.status_blob_config.uri
        )
        try:
            new_status_str = storage.read_text(path)
            try:
                new_task_run_status = TaskRunStatus(new_status_str)
                new_status = TaskStateStatus.from_task_run_status(new_task_run_status)
            except ValueError:
                self.set_failed(errors=[f"Invalid status update: {new_status_str}"])
                return

            # Only allow task to report running or completing
            if new_status == TaskStateStatus.RUNNING:
                self.change_status(new_status)

        except FileNotFoundError:
            pass

    def get_log_uri(self, storage: Storage) -> Optional[str]:
        log_uri = self.prepared_task.task_run_message.config.log_blob_config.uri
        path = storage.get_path(log_uri)
        if storage.file_exists(path):
            return log_uri
        return None


@dataclass
class JobPartitionState:
    """The state of an executing PCTasks job.

    This class should only be used on a single thread.
    """

    job_part_submit_msg: JobPartitionSubmitMessage
    job_part_run_record_id: str
    task_queue: List[TaskDefinition]
    task_outputs: Dict[str, Any] = field(default_factory=dict)

    current_task: Optional[TaskState] = None
    status: JobPartitionStateStatus = JobPartitionStateStatus.NEW

    @property
    def job_id(self) -> str:
        return self.job_part_submit_msg.job_id

    @property
    def run_id(self) -> str:
        return self.job_part_submit_msg.run_id

    def prepare_next_task(self, settings: RunSettings) -> None:
        next_task_config = next(iter(self.task_queue), None)
        if next_task_config:
            task_data = self.job_part_submit_msg.job_partition.task_data.get(
                next_task_config.id
            )
            if not task_data:
                raise Exception(
                    "Task preparation failed due to internal runner error. "
                    f"Task data not found for task {next_task_config.id}"
                )

            copied_task = next_task_config.__class__.parse_obj(next_task_config.dict())
            copied_task.args = template_args(
                copied_task.args,
                job_outputs=self.job_part_submit_msg.job_outputs,
                task_outputs=self.task_outputs,
                trigger_event=None,
            )

            next_task_submit_message = TaskSubmitMessage(
                dataset_id=self.job_part_submit_msg.dataset_id,
                run_id=self.job_part_submit_msg.run_id,
                job_id=self.job_part_submit_msg.job_id,
                partition_id=self.job_part_submit_msg.partition_id,
                tokens=self.job_part_submit_msg.tokens,
                definition=copied_task,
                target_environment=self.job_part_submit_msg.target_environment,
            )

            self.current_task = TaskState(
                prepared_task=prepare_task(
                    next_task_submit_message,
                    self.job_part_submit_msg.run_id,
                    task_data=task_data,
                    settings=settings,
                ),
                job_part_run_record_id=self.job_part_run_record_id,
            )
        else:
            self.current_task = None
        self.current_submit_result = None
        self.task_queue = self.task_queue[1:]

    @classmethod
    def create(
        cls,
        job_part_submit_msg: JobPartitionSubmitMessage,
        job_part_run_record_id: str,
        settings: RunSettings,
    ) -> "JobPartitionState":
        """Creates a JobState from a JobSubmitMessage.

        Prepares the first task for execution.
        """
        job_state = cls(
            job_part_submit_msg=job_part_submit_msg,
            job_part_run_record_id=job_part_run_record_id,
            current_task=None,
            task_queue=job_part_submit_msg.job_partition.definition.tasks[:],
        )
        job_state.prepare_next_task(settings)
        return job_state
