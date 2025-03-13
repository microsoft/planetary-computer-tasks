import logging
from typing import Any, Dict, List, Optional, Tuple, Union

from pydantic import Field

from pctasks.core.constants import TASK_SUBMIT_MESSAGE_TYPE
from pctasks.core.models.base import PCBaseModel, RunRecordId
from pctasks.core.models.config import BlobConfig
from pctasks.core.models.run import TaskRunStatus
from pctasks.core.models.task import (
    CompletedTaskResult,
    FailedTaskResult,
    TaskDefinition,
    TaskResultType,
    TaskRunMessage,
    WaitTaskResult,
)
from pctasks.core.models.tokens import StorageAccountTokens
from pctasks.core.models.workflow import JobDefinition, WorkflowSubmitMessage
from pctasks.core.utils import StrEnum

logger = logging.getLogger(__name__)


class TaskSubmitMessage(PCBaseModel):
    dataset_id: str
    run_id: str
    job_id: str
    partition_id: str
    definition: TaskDefinition
    tags: Optional[Dict[str, str]] = None
    target_environment: Optional[str] = None
    related_tasks: Optional[List[Tuple[str, str]]] = None
    tokens: Optional[Dict[str, StorageAccountTokens]] = None
    wait_retries: int = 0
    type: str = Field(default=TASK_SUBMIT_MESSAGE_TYPE, frozen=True)

    def get_run_record_id(self) -> RunRecordId:
        return RunRecordId(
            dataset_id=self.dataset_id,
            run_id=self.run_id,
            job_id=self.job_id,
            task_id=self.definition.id,
        )


class PreparedTaskData(PCBaseModel):
    image: str
    environment: Optional[Dict[str, str]]
    tags: Optional[Dict[str, str]]
    tokens: Optional[Dict[str, StorageAccountTokens]]
    runner_info: Dict[str, Any]


class PreparedTaskSubmitMessage(PCBaseModel):
    task_submit_message: TaskSubmitMessage
    task_run_message: TaskRunMessage
    task_input_blob_config: BlobConfig
    task_data: PreparedTaskData


class PreparedWorkflowSubmitMessage(PCBaseModel):
    workflow_submit_message: WorkflowSubmitMessage
    # runner_settings:


class SuccessfulTaskSubmitResult(PCBaseModel):
    success: bool = True
    task_runner_id: Dict[str, Any]


class FailedTaskSubmitResult(PCBaseModel):
    success: bool = False
    errors: List[str]


class TaskSubmitResult(PCBaseModel):
    result: Union[SuccessfulTaskSubmitResult, FailedTaskSubmitResult]


class TaskPollMessage(PCBaseModel):
    executor_id: Dict[str, Any]
    run_record_id: RunRecordId
    parent_instance_id: Optional[str]
    signal_key: str
    previous_poll_count: int = 0


class TaskPollResult(PCBaseModel):
    task_status: TaskRunStatus
    poll_errors: Optional[List[str]] = None

    @property
    def is_finished(self) -> bool:
        return (
            self.task_status == TaskRunStatus.COMPLETED
            or self.task_status == TaskRunStatus.FAILED
            or self.task_status == TaskRunStatus.CANCELLED
        )


class HandledTaskResult(PCBaseModel):
    result: Union[CompletedTaskResult, WaitTaskResult, FailedTaskResult]
    log_uris: Optional[List[str]] = None


class HandleTaskResultMessage(PCBaseModel):
    run_record_id: RunRecordId
    task_result_type: TaskResultType
    submit_result: SuccessfulTaskSubmitResult
    target_environment: Optional[str] = None
    errors: Optional[List[str]] = None
    log_uri: str
    """The URI of the task log file."""


class JobPartition(PCBaseModel):
    definition: JobDefinition
    partition_id: str
    task_data: List[PreparedTaskData]


class JobPartitionSubmitMessage(PCBaseModel):
    job_partition: JobPartition
    dataset_id: str
    run_id: str
    job_id: str
    partition_id: str
    tokens: Optional[Dict[str, StorageAccountTokens]] = None
    target_environment: Optional[str] = None
    job_outputs: Dict[str, Any]
    trigger_event: Optional[Dict[str, Any]] = None

    def get_run_record_id(self) -> RunRecordId:
        return RunRecordId(
            dataset_id=self.dataset_id,
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


class NotificationSubmitResult(PCBaseModel):
    error: Optional[str] = None
