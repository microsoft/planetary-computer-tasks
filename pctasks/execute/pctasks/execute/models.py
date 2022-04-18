import logging
from typing import Any, Dict, List, Optional, Tuple, Union

from pydantic import Field

from pctasks.core.constants import TASK_SUBMIT_MESSAGE_TYPE
from pctasks.core.models.base import PCBaseModel, RunRecordId
from pctasks.core.models.dataset import DatasetIdentifier
from pctasks.core.models.record import (
    JobRunRecord,
    JobRunStatus,
    RecordType,
    TaskRunRecord,
    TaskRunStatus,
    WorkflowRunGroupRecord,
    WorkflowRunGroupStatus,
    WorkflowRunRecord,
    WorkflowRunStatus,
)
from pctasks.core.models.task import (
    CompletedTaskResult,
    FailedTaskResult,
    TaskConfig,
    TaskResultType,
    WaitTaskResult,
)
from pctasks.core.models.tokens import StorageAccountTokens
from pctasks.core.models.workflow import JobConfig
from pctasks.core.utils import StrEnum

logger = logging.getLogger(__name__)


class TaskSubmitMessage(PCBaseModel):
    instance_id: Optional[str]
    """The instance ID of the task orchestrator."""
    dataset: DatasetIdentifier
    run_id: str
    job_id: str
    config: TaskConfig
    tags: Optional[Dict[str, str]] = None
    target_environment: Optional[str] = None
    related_tasks: Optional[List[Tuple[str, str]]] = None
    tokens: Optional[Dict[str, StorageAccountTokens]] = None
    wait_retries: int = 0
    type: str = Field(default=TASK_SUBMIT_MESSAGE_TYPE, const=True)

    def get_run_record_id(self) -> RunRecordId:
        return RunRecordId(
            dataset_id=str(self.dataset),
            run_id=self.run_id,
            job_id=self.job_id,
            task_id=self.config.id,
        )


class SuccessfulSubmitResult(PCBaseModel):
    success: bool = True
    executor_id: Dict[str, Any]
    signal_key: str
    output_uri: str
    log_uri: str
    output_account_url: Optional[str] = None


class FailedSubmitResult(PCBaseModel):
    success: bool = False
    errors: List[str]


class TaskSubmitResult(PCBaseModel):
    result: Union[SuccessfulSubmitResult, FailedSubmitResult]


class TaskPollMessage(PCBaseModel):
    executor_id: Dict[str, Any]
    run_record_id: RunRecordId
    parent_instance_id: Optional[str]
    signal_key: str
    previous_poll_count: int = 0


class TaskPollResult(PCBaseModel):
    task_status: TaskRunStatus
    poll_errors: Optional[List[str]] = None


class HandledTaskResult(PCBaseModel):
    result: Union[CompletedTaskResult, WaitTaskResult, FailedTaskResult]
    log_uris: Optional[List[str]] = None


class HandleTaskResultMessage(PCBaseModel):
    run_record_id: RunRecordId
    task_result_type: TaskResultType
    submit_result: SuccessfulSubmitResult
    target_environment: Optional[str] = None
    errors: Optional[List[str]] = None
    log_uri: str
    """The URI of the task log file."""


class JobSubmitMessage(PCBaseModel):
    job: JobConfig
    dataset: DatasetIdentifier
    run_id: str
    job_id: str
    tokens: Optional[Dict[str, StorageAccountTokens]] = None
    target_environment: Optional[str] = None
    job_outputs: Dict[str, Any]
    trigger_event: Optional[Dict[str, Any]] = None

    def get_run_record_id(self) -> RunRecordId:
        return RunRecordId(
            dataset_id=str(self.dataset),
            run_id=self.run_id,
            job_id=self.job_id,
        )


class JobResultMessage(PCBaseModel):
    job_id: str
    errors: Optional[List[str]] = None
    task_outputs: Optional[Dict[str, Any]] = None


class MessageEvent(StrEnum):
    MESSAGE_RECEIVED = "message_received"
    MESSAGE_SENT = "message_sent"


class RecordUpdate(PCBaseModel):
    type: str

    errors: Optional[List[str]] = None


class CreateWorkflowRunGroupRecordUpdate(RecordUpdate):
    type: str = Field(default=f"Create{RecordType.WORKFLOW_GROUP}", const=True)
    record: WorkflowRunGroupRecord


class WorkflowRunGroupRecordUpdate(RecordUpdate):
    type: str = Field(default=f"Update{RecordType.WORKFLOW_GROUP}", const=True)
    dataset: DatasetIdentifier
    group_id: str
    status: WorkflowRunGroupStatus

    def update_record(self, record: WorkflowRunGroupRecord) -> None:
        record.status = self.status


class CreateWorkflowRunRecordUpdate(RecordUpdate):
    type: str = Field(default=f"Create{RecordType.WORKFLOW}", const=True)
    record: WorkflowRunRecord


class WorkflowRunRecordUpdate(RecordUpdate):
    type: str = Field(default=f"Update{RecordType.WORKFLOW}", const=True)
    dataset: DatasetIdentifier
    run_id: str
    status: WorkflowRunStatus

    def get_run_record_id(self) -> RunRecordId:
        return RunRecordId(dataset_id=str(self.dataset), run_id=self.run_id)

    def update_record(self, record: WorkflowRunRecord) -> None:
        record.status = self.status
        if self.errors:
            record.errors = (record.errors or []) + self.errors


class CreateJobRunRecordUpdate(RecordUpdate):
    type: str = Field(default=f"Create{RecordType.JOB}", const=True)
    record: JobRunRecord


class JobRunRecordUpdate(RecordUpdate):
    type: str = Field(default=f"Update{RecordType.JOB}", const=True)
    run_id: str
    job_id: str
    status: JobRunStatus

    def get_run_record_id(self) -> RunRecordId:
        return RunRecordId(run_id=self.run_id, job_id=self.job_id)

    def update_record(self, record: JobRunRecord) -> None:
        record.status = self.status
        if self.errors:
            record.errors = (record.errors or []) + self.errors


class CreateTaskRunRecordUpdate(RecordUpdate):
    type: str = Field(default=f"Create{RecordType.TASK}", const=True)
    record: TaskRunRecord


class TaskRunRecordUpdate(RecordUpdate):
    type: str = Field(default=f"Update{RecordType.TASK}", const=True)
    run_id: str
    job_id: str
    task_id: str
    status: TaskRunStatus
    log_uris: Optional[List[str]] = None

    def get_run_record_id(self) -> RunRecordId:
        return RunRecordId(run_id=self.run_id, job_id=self.job_id, task_id=self.task_id)

    def update_record(self, record: TaskRunRecord) -> None:
        record.status = self.status
        if self.errors:
            record.errors = (record.errors or []) + self.errors
        if self.log_uris:
            record.log_uris = (record.log_uris or []) + self.log_uris


class UpdateRecordMessage(PCBaseModel):
    update: Union[
        CreateWorkflowRunGroupRecordUpdate,
        WorkflowRunGroupRecordUpdate,
        CreateWorkflowRunRecordUpdate,
        WorkflowRunRecordUpdate,
        CreateJobRunRecordUpdate,
        JobRunRecordUpdate,
        CreateTaskRunRecordUpdate,
        TaskRunRecordUpdate,
    ]


class UpdateRecordResult(PCBaseModel):
    error: Optional[str] = None


class NotificationSubmitResult(PCBaseModel):
    error: Optional[str] = None
