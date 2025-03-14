from base64 import b64decode, b64encode
from typing import Any, Dict, List, Optional, Union

import orjson
from pydantic import Field, field_validator, model_validator
from typing_extensions import Self

from pctasks.core.constants import (
    TASK_CONFIG_SCHEMA_VERSION,
    TASK_RESULT_SCHEMA_VERSION,
    TASK_RUN_CONFIG_SCHEMA_VERSION,
    TASK_RUN_SIGNAL_SCHEMA_VERSION,
)
from pctasks.core.models.base import PCBaseModel
from pctasks.core.models.config import BlobConfig, CodeConfig
from pctasks.core.models.event import NotificationMessage
from pctasks.core.models.tokens import StorageAccountTokens
from pctasks.core.tables.base import InvalidTableKeyError, validate_table_key
from pctasks.core.utils import StrEnum


class TaskDefinition(PCBaseModel):
    id: str
    image: Optional[str] = None
    image_key: Optional[str] = Field(default=None, validation_alias="image-key")
    code: Optional[CodeConfig] = None
    task: str
    args: Dict[str, Any] = {}
    tags: Optional[Dict[str, str]] = None
    environment: Optional[Dict[str, str]] = None
    schema_version: str = TASK_CONFIG_SCHEMA_VERSION

    @model_validator(mode="after")
    def image_key_or_image_validator(self) -> Self:
        if self.image_key and self.image:
            raise ValueError("Specify either image_key or image, but not both.")
        elif not (self.image_key or self.image):
            raise ValueError("Must specify either image_key or image, at most one")
        return self

    @field_validator("id", mode="after")
    def validate_id(cls, v: Optional[str]) -> Optional[str]:
        if v:
            try:
                validate_table_key(v)
            except InvalidTableKeyError as e:
                raise ValueError(f"Invalid task id '{v}': {e.INFO_MESSAGE}")
        return v


class TaskRunConfig(PCBaseModel):
    """Passed to the task run"""

    image: str
    run_id: str
    job_id: str
    partition_id: str
    task_id: str
    task: str
    code_src_blob_config: Optional[BlobConfig] = None
    code_requirements_blob_config: Optional[BlobConfig] = None
    code_pip_options: Optional[List[str]] = None
    environment: Optional[Dict[str, str]] = None
    tokens: Optional[Dict[str, StorageAccountTokens]] = None
    status_blob_config: BlobConfig
    output_blob_config: BlobConfig
    log_blob_config: BlobConfig
    event_logger_app_insights_key: Optional[str] = None
    schema_version: str = Field(default=TASK_RUN_CONFIG_SCHEMA_VERSION, frozen=True)

    def get_run_record_id(self) -> str:
        return f"{self.run_id}/{self.job_id}/{self.partition_id}/{self.task_id}"


class TaskRunMessage(PCBaseModel):
    args: Dict[str, Any]
    config: TaskRunConfig

    def encoded(self) -> str:
        return b64encode(self.json(exclude_none=True).encode("utf-8")).decode("utf-8")

    @classmethod
    def decode(cls, msg_text: str) -> "TaskRunMessage":
        return cls.model_validate(
            orjson.loads(b64decode(msg_text.encode("utf-8")).decode("utf-8"))
        )


class TaskResultType(StrEnum):
    COMPLETED = "completed"
    """Task run is completed successfully."""

    FAILED = "failed"
    """Task run completed with failure."""

    WAIT = "wait"
    """Task not ready to run."""


class TaskResult(PCBaseModel):
    schema_version: str = Field(default=TASK_RESULT_SCHEMA_VERSION, frozen=True)
    status: TaskResultType

    @staticmethod
    def completed(
        output: Dict[str, Any] = {},
        notifications: Optional[List[NotificationMessage]] = None,
        task_uri: Optional[str] = None,
        task_item_id: Optional[str] = None,
    ) -> "CompletedTaskResult":
        return CompletedTaskResult(
            notifications=notifications,
            output=output,
            task_uri=task_uri,
            task_item_id=task_item_id,
        )

    @staticmethod
    def wait(
        wait_seconds: Optional[int] = None, message: Optional[str] = None
    ) -> "WaitTaskResult":
        return WaitTaskResult(wait_seconds=wait_seconds, message=message)

    @staticmethod
    def failed(
        errors: Optional[List[str]] = None,
    ) -> "FailedTaskResult":
        return FailedTaskResult(errors=errors)

    @classmethod
    def parse_subclass(
        cls, obj: Dict[str, Any]
    ) -> Union["CompletedTaskResult", "WaitTaskResult", "FailedTaskResult"]:
        if obj["status"] == TaskResultType.COMPLETED:
            return CompletedTaskResult.model_validate(obj)
        elif obj["status"] == TaskResultType.WAIT:
            return WaitTaskResult.model_validate(obj)
        elif obj["status"] == TaskResultType.FAILED:
            return FailedTaskResult.model_validate(obj)
        else:
            raise ValueError(f"Unknown task result status: {obj['status']}")


class CompletedTaskResult(TaskResult):
    status: TaskResultType = Field(default=TaskResultType.COMPLETED, frozen=True)
    output: Dict[str, Any] = {}
    notifications: Optional[List[NotificationMessage]] = None
    task_uri: Optional[str] = None
    task_item_id: Optional[str] = None


class WaitTaskResult(TaskResult):
    """Result returned by a task when it is not yet ready to run."""

    status: TaskResultType = Field(default=TaskResultType.WAIT, frozen=True)
    wait_seconds: Optional[int] = None
    message: Optional[str] = None


class FailedTaskResult(TaskResult):
    status: TaskResultType = Field(default=TaskResultType.FAILED, frozen=True)
    errors: Optional[List[str]] = None


class TaskOutput(PCBaseModel):
    result: Union[CompletedTaskResult, WaitTaskResult]


class TaskRunSignal(PCBaseModel):
    signal_key: str
    task_result_type: TaskResultType


class TaskRunSignalMessage(PCBaseModel):
    signal_target_id: str
    data: TaskRunSignal
    schema_version: str = Field(default=TASK_RUN_SIGNAL_SCHEMA_VERSION, frozen=True)
