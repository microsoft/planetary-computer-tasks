from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import Field, model_validator
from typing_extensions import Self

from pctasks.core.models.base import PCBaseModel
from pctasks.core.models.event import CloudEvent
from pctasks.core.models.record import Record
from pctasks.core.models.task import TaskDefinition
from pctasks.core.models.utils import tzutc_now
from pctasks.core.models.workflow import (
    JobDefinition,
    WorkflowRunStatus,
    WorkflowSubmitMessage,
)
from pctasks.core.utils import StrEnum


class RunRecordType(StrEnum):
    WORKFLOW_RUN = "WorkflowRun"
    JOB_RUN = "JobRun"
    JOB_PARTITION_RUN = "JobPartitionRun"
    TASK_RUN = "TaskRun"


class TaskRunStatus(StrEnum):

    RECEIVED = "received"
    """Task run was received by the executor (e.g. Azure Batch)."""

    PENDING = "pending"
    """Task run is being processed before submission."""

    SUBMITTING = "submitting"
    """Task run is in the process of being submitted."""

    SUBMITTED = "submitted"
    """Task run was submitted to the executor (e.g. Azure Batch)."""

    STARTING = "starting"
    """Task run is starting."""

    RUNNING = "running"
    """Task run is currently running."""

    WAITING = "waiting"
    """Task is waiting for conditions to be met."""

    COMPLETING = "completing"
    """Task run was successful, awaiting orchestrator completion."""

    COMPLETED = "completed"
    """Task run is completed successfully."""

    FAILED = "failed"
    """Task run completed with failure."""

    CANCELLED = "cancelled"
    """Task run was cancelled."""


class JobPartitionRunStatus(StrEnum):
    # Keep in sync with triggers

    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PENDING = "pending"


class JobRunStatus(StrEnum):

    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"
    PENDING = "pending"


class StatusHistoryEntry(PCBaseModel):
    status: str
    timestamp: datetime


class RunRecord(Record):
    status: str
    status_history: List[StatusHistoryEntry] = []

    def set_status(self, status: str) -> None:
        self.status = status
        self.status_history.append(
            StatusHistoryEntry(status=status, timestamp=tzutc_now())
        )

    @model_validator(mode="after")
    def _validate_status_history(self) -> Self:
        # Always ensure the status history is valid
        if not self.status_history:
            self.status_history = [
                StatusHistoryEntry(status=self.status, timestamp=tzutc_now())
            ]
        return self


class TaskRunRecord(RunRecord):
    type: str = Field(default=RunRecordType.TASK_RUN, frozen=True)

    run_id: str
    job_id: str
    partition_id: str
    task_id: str

    status: TaskRunStatus

    log_uri: Optional[str] = None

    errors: Optional[List[str]] = None

    def get_id(self) -> str:
        return f"{self.run_id}:{self.job_id}:{self.partition_id}:{self.task_id}"

    def add_errors(self, errors: List[str]) -> None:
        if self.errors is None:
            self.errors = []
        self.errors.extend(errors)

    @classmethod
    def from_task_definition(
        cls, task_def: TaskDefinition, run_id: str, job_id: str, partition_id: str
    ) -> "TaskRunRecord":
        return cls(
            run_id=run_id,
            job_id=job_id,
            partition_id=partition_id,
            task_id=task_def.id,
            status=TaskRunStatus.PENDING,
        )


class JobPartitionRunRecord(RunRecord):
    type: str = Field(default=RunRecordType.JOB_PARTITION_RUN, frozen=True)

    run_id: str
    job_id: str
    partition_id: str

    status: JobPartitionRunStatus

    tasks: List[TaskRunRecord]

    def get_id(self) -> str:
        return self.id_from(
            run_id=self.run_id, job_id=self.job_id, partition_id=self.partition_id
        )

    def get_task(self, task_id: str) -> Optional[TaskRunRecord]:
        for task in self.tasks:
            if task.task_id == task_id:
                return task
        return None

    @classmethod
    def from_definition(
        cls,
        partition_id: str,
        job_definition: JobDefinition,
        run_id: str,
        # TODO(3.11) use StrEnum
        status: JobPartitionRunStatus = JobPartitionRunStatus.PENDING,  # type: ignore[assignment]  # noqa: E501
    ) -> "JobPartitionRunRecord":
        job_id = job_definition.get_id()
        return cls(
            status=status,
            run_id=run_id,
            job_id=job_id,
            partition_id=partition_id,
            tasks=[
                TaskRunRecord.from_task_definition(task, run_id, job_id, partition_id)
                for task in job_definition.tasks
            ],
        )

    @staticmethod
    def id_from(run_id: str, job_id: str, partition_id: str) -> str:
        return f"{run_id}:{job_id}:{partition_id}"


class JobRunRecord(RunRecord):
    type: str = Field(default=RunRecordType.JOB_RUN, frozen=True)

    run_id: str
    job_id: str

    status: JobRunStatus

    job_partition_counts: Dict[str, int] = {
        JobPartitionRunStatus.PENDING: 0,
        JobPartitionRunStatus.RUNNING: 0,
        JobPartitionRunStatus.COMPLETED: 0,
        JobPartitionRunStatus.FAILED: 0,
        JobPartitionRunStatus.CANCELLED: 0,
    }

    errors: Optional[List[str]] = None

    def get_id(self) -> str:
        return f"{self.run_id}:{self.job_id}"

    def add_errors(self, errors: List[str]) -> None:
        if self.errors is None:
            self.errors = []
        self.errors.extend(errors)

    @classmethod
    def from_job(cls, job: JobDefinition, run_id: str) -> "JobRunRecord":
        return cls(
            run_id=run_id,
            job_id=job.get_id(),
            status=JobRunStatus.PENDING,
        )


class WorkflowRunRecord(RunRecord):
    type: str = Field(default=RunRecordType.WORKFLOW_RUN, frozen=True)

    dataset_id: str
    run_id: str

    status: WorkflowRunStatus

    workflow_id: str
    trigger_event: Optional[CloudEvent] = None
    args: Optional[Dict[str, Any]] = None

    log_uri: Optional[str] = None

    jobs: List[JobRunRecord]

    def get_id(self) -> str:
        return self.run_id

    def get_job_run(self, job_id: str) -> Optional[JobRunRecord]:
        for job in self.jobs:
            if job.job_id == job_id:
                return job
        return None

    @classmethod
    def from_submit_message(
        cls, submit_msg: WorkflowSubmitMessage
    ) -> "WorkflowRunRecord":
        jobs = [
            JobRunRecord.from_job(job, submit_msg.run_id)
            for job in submit_msg.workflow.definition.jobs.values()
        ]
        return cls(
            dataset_id=submit_msg.workflow.dataset_id,
            run_id=submit_msg.run_id,
            status=WorkflowRunStatus.SUBMITTED,
            workflow_id=submit_msg.workflow.id,
            trigger_event=submit_msg.trigger_event,
            args=submit_msg.args,
            jobs=jobs,
        )
