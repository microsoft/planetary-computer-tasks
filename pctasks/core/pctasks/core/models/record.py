from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import Field, validator

from pctasks.core.constants import RECORD_SCHEMA_VERSION
from pctasks.core.models.base import PCBaseModel
from pctasks.core.models.dataset import DatasetIdentifier
from pctasks.core.models.event import CloudEvent
from pctasks.core.models.workflow import WorkflowConfig
from pctasks.core.tables.base import InvalidTableKeyError, validate_table_key
from pctasks.core.utils import StrEnum
from pctasks.core.version import __version__


class RecordType(StrEnum):
    WORKFLOW_GROUP = "WorkflowGroup"
    WORKFLOW = "Workflow"
    JOB = "Job"
    TASK = "Task"


class TaskRunStatus(StrEnum):

    RECEIVED = "received"
    """Task run was received by the executor (e.g. Azure Batch)."""

    PENDING = "pending"
    """Task run is being processed before submission."""

    SUBMITTING = "submitting"
    """Task run is in the process of being submitted."""

    SUBMITTED = "submitted"
    """Task run was submitted to the executor (e.g. Azure Batch)."""

    STARTING = "staring"
    """Task run is starting."""

    RUNNING = "running"
    """Task run is currently running."""

    WAITING = "waiting"
    """Task is waiting for conditions to be met."""

    COMPLETED = "completed"
    """Task run is completed successfully."""

    FAILED = "failed"
    """Task run completed with failure."""

    CANCELLED = "cancelled"
    """Task run was cancelled."""


class JobRunStatus(StrEnum):

    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PENDING = "pending"
    NOTASKS = "notasks"


class WorkflowRunStatus(StrEnum):

    RECEIVED = "received"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class WorkflowRunGroupStatus(StrEnum):

    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class RunRecord(PCBaseModel):
    type: str
    created: datetime = Field(default_factory=datetime.utcnow)
    updated: datetime = Field(default_factory=datetime.utcnow)

    errors: Optional[List[str]] = None

    status: str

    schema_version: str = RECORD_SCHEMA_VERSION

    def set_update_time(self) -> None:
        self.updated = datetime.utcnow()


class TaskRunRecord(RunRecord):
    type: str = Field(default=RecordType.TASK, const=True)

    run_id: str
    job_id: str
    task_id: str

    status: TaskRunStatus
    """Status of the task run."""

    log_uris: Optional[List[str]] = None
    """URIs to log files for this run."""

    version: str = __version__

    def update_status(self, status: TaskRunStatus) -> None:
        self.status = status
        self.set_update_time()


class JobRunRecord(RunRecord):
    type: str = Field(default=RecordType.JOB, const=True)

    run_id: str
    job_id: str

    status: JobRunStatus

    @validator("job_id")
    def validate_job_id(cls, v: Optional[str]) -> Optional[str]:
        if v:
            try:
                validate_table_key(v)
            except InvalidTableKeyError as e:
                raise ValueError(f"Invalid job id '{v}': {e.INFO_MESSAGE}")
        return v


class WorkflowRunRecord(RunRecord):
    type: str = Field(default=RecordType.WORKFLOW, const=True)

    dataset: DatasetIdentifier
    run_id: str

    status: WorkflowRunStatus

    workflow: WorkflowConfig
    trigger_event: Optional[CloudEvent] = None
    args: Optional[Dict[str, Any]] = None

    created: datetime = Field(default_factory=datetime.utcnow)
    updated: datetime = Field(default_factory=datetime.utcnow)


class WorkflowRunGroupRecord(RunRecord):
    type: str = Field(default=RecordType.WORKFLOW_GROUP, const=True)

    dataset: DatasetIdentifier
    group_id: str

    status: WorkflowRunGroupStatus

    @validator("group_id")
    def validate_group_id(cls, v: Optional[str]) -> Optional[str]:
        if v:
            try:
                validate_table_key(v)
            except InvalidTableKeyError as e:
                raise ValueError(f"Invalid group id '{v}': {e.INFO_MESSAGE}")
        return v
