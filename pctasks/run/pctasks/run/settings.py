from enum import Enum
from typing import Any, Dict, Optional
from urllib.parse import urlparse

from pydantic import validator

from pctasks.core.constants import (
    DEFAULT_DATASET_TABLE_NAME,
    DEFAULT_IMAGE_KEY_TABLE_NAME,
    DEFAULT_JOB_RUN_RECORD_TABLE_NAME,
    DEFAULT_LOG_CONTAINER,
    DEFAULT_NOTIFICATIONS_QUEUE_NAME,
    DEFAULT_TASK_IO_CONTAINER,
    DEFAULT_TASK_RUN_RECORD_TABLE_NAME,
    DEFAULT_WORKFLOW_RUN_GROUP_RECORD_TABLE_NAME,
    DEFAULT_WORKFLOW_RUN_RECORD_TABLE_NAME,
)
from pctasks.core.models.base import PCBaseModel
from pctasks.core.models.config import QueueConnStrConfig
from pctasks.core.settings import PCTasksSettings
from pctasks.core.storage.blob import BlobStorage
from pctasks.core.tables.config import ImageKeyEntryTable
from pctasks.core.tables.dataset import DatasetIdentifierTable
from pctasks.core.tables.record import (
    JobRunRecordTable,
    TaskRunRecordTable,
    WorkflowRunGroupRecordTable,
    WorkflowRunRecordTable,
)


class TaskRunnerType(str, Enum):
    ARGO = "argo"
    BATCH = "batch"
    LOCAL = "local"


class BatchSettings(PCBaseModel):
    url: str
    key: str
    default_pool_id: str
    submit_threads: int

    def get_batch_name(self) -> str:
        return urlparse(self.url).netloc.split(".")[0]


class NotificationQueueConnStrConfig(QueueConnStrConfig):
    queue_name: str = DEFAULT_NOTIFICATIONS_QUEUE_NAME


class RunSettings(PCTasksSettings):
    @classmethod
    def section_name(cls) -> str:
        return "run"

    remote_runner_threads: int = 50
    default_task_wait_seconds: int = 60
    max_wait_retries: int = 10
    task_poll_seconds: int = 30
    check_output_seconds: int = 3

    # Dev
    local_executor_url: Optional[str] = None
    local_secrets: bool = False

    notification_queue: NotificationQueueConnStrConfig

    # Tables
    tables_account_url: str
    tables_account_name: str
    tables_account_key: str
    image_key_table_name: str = DEFAULT_IMAGE_KEY_TABLE_NAME
    dataset_table_name: str = DEFAULT_DATASET_TABLE_NAME
    task_run_record_table_name: str = DEFAULT_TASK_RUN_RECORD_TABLE_NAME
    job_run_record_table_name: str = DEFAULT_JOB_RUN_RECORD_TABLE_NAME
    workflow_run_record_table_name: str = DEFAULT_WORKFLOW_RUN_RECORD_TABLE_NAME
    workflow_run_group_record_table_name: str = (
        DEFAULT_WORKFLOW_RUN_GROUP_RECORD_TABLE_NAME
    )

    # Blob
    blob_account_url: str
    blob_account_name: str
    blob_account_key: str
    log_blob_container: str = DEFAULT_LOG_CONTAINER
    task_io_blob_container: str = DEFAULT_TASK_IO_CONTAINER

    # Batch
    batch_url: Optional[str] = None
    batch_key: Optional[str] = None
    batch_default_pool_id: Optional[str] = None
    batch_submit_threads: int = 0

    # Argo
    argo_host: Optional[str] = None
    argo_token: Optional[str] = None
    argo_namespace: str = "argo"

    # KeyVault
    keyvault_url: Optional[str] = None
    keyvault_sp_tenant_id: Optional[str] = None
    keyvault_sp_client_id: Optional[str] = None
    keyvault_sp_client_secret: Optional[str] = None

    # Type of task runner to use.
    task_runner_type: TaskRunnerType = TaskRunnerType.BATCH

    @property
    def batch_settings(self) -> BatchSettings:
        if not (self.batch_url and self.batch_key and self.batch_default_pool_id):
            raise ValueError("Azure Batch settings not configured")

        return BatchSettings(
            url=self.batch_url,
            key=self.batch_key,
            default_pool_id=self.batch_default_pool_id,
            submit_threads=self.batch_submit_threads,
        )

    @validator("batch_url", always=True)
    def batch_url_validator(
        cls, v: Optional[str], values: Dict[str, Any]
    ) -> Optional[str]:
        if values.get("local_executor_url") is None:
            if not v:
                raise ValueError("Must specify batch_url.")
        if v:
            parsed = urlparse(v)
            if not parsed.scheme or not parsed.netloc:
                raise ValueError(f"Invalid batch_url: {v}")
        return v

    @validator("batch_key", always=True)
    def batch_key_validator(
        cls, v: Optional[str], values: Dict[str, Any]
    ) -> Optional[str]:
        if values.get("batch_url"):
            if not v:
                raise ValueError("Must specify batch_key.")
        return v

    @validator("keyvault_url", always=True)
    def keyvault_url_validator(
        cls, v: Optional[str], values: Dict[str, Any]
    ) -> Optional[str]:
        if not values.get("local_secrets"):
            if not v:
                raise ValueError("Must specify keyvault_url.")
        return v

    @validator("task_runner_type", always=True)
    def _task_runner_type_validator(
        cls, v: TaskRunnerType, values: Dict[str, Any]
    ) -> TaskRunnerType:
        if v == TaskRunnerType.LOCAL:
            if values.get("local_executor_url") is None:
                raise ValueError(
                    "Must specify local_executor_url for local remote runner type."
                )

        if v == TaskRunnerType.ARGO:
            if values.get("argo_host") is None:
                raise ValueError("Must specify argo_host for argo remote runner type.")
            if values.get("argo_token") is None:
                raise ValueError("Must specify argo_token for argo remote runner type.")

        if v == TaskRunnerType.BATCH:
            if values.get("batch_url") is None:
                raise ValueError("Must specify batch_url for batch remote runner type.")
            if values.get("batch_key") is None:
                raise ValueError("Must specify batch_key for batch remote runner type.")
            if values.get("batch_default_pool_id") is None:
                raise ValueError(
                    "Must specify batch_default_pool_id for batch remote runner type."
                )

        return v

    # Don't cache tables; executor is not thread-safe

    def get_image_key_table(self) -> ImageKeyEntryTable:
        return ImageKeyEntryTable.from_account_key(
            account_url=self.tables_account_url,
            account_name=self.tables_account_name,
            account_key=self.tables_account_key,
            table_name=self.image_key_table_name,
        )

    def get_dataset_table(self) -> DatasetIdentifierTable:
        return DatasetIdentifierTable.from_account_key(
            account_url=self.tables_account_url,
            account_name=self.tables_account_name,
            account_key=self.tables_account_key,
            table_name=self.dataset_table_name,
        )

    def get_task_run_record_table(self) -> TaskRunRecordTable:
        return TaskRunRecordTable.from_account_key(
            account_url=self.tables_account_url,
            account_name=self.tables_account_name,
            account_key=self.tables_account_key,
            table_name=self.task_run_record_table_name,
        )

    def get_job_run_record_table(self) -> JobRunRecordTable:
        return JobRunRecordTable.from_account_key(
            account_url=self.tables_account_url,
            account_name=self.tables_account_name,
            account_key=self.tables_account_key,
            table_name=self.job_run_record_table_name,
        )

    def get_workflow_run_record_table(self) -> WorkflowRunRecordTable:
        return WorkflowRunRecordTable.from_account_key(
            account_url=self.tables_account_url,
            account_name=self.tables_account_name,
            account_key=self.tables_account_key,
            table_name=self.workflow_run_record_table_name,
        )

    def get_workflow_run_group_record_table(self) -> WorkflowRunGroupRecordTable:
        return WorkflowRunGroupRecordTable.from_account_key(
            account_url=self.tables_account_url,
            account_name=self.tables_account_name,
            account_key=self.tables_account_key,
            table_name=self.workflow_run_group_record_table_name,
        )

    def get_task_io_storage(self) -> BlobStorage:
        return BlobStorage.from_account_key(
            f"blob://{self.blob_account_name}/{self.task_io_blob_container}",
            account_key=self.blob_account_key,
            account_url=self.blob_account_url,
        )

    def get_log_storage(self) -> BlobStorage:
        return BlobStorage.from_account_key(
            f"blob://{self.blob_account_name}/{self.log_blob_container}",
            account_key=self.blob_account_key,
            account_url=self.blob_account_url,
        )
