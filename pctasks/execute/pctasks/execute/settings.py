from typing import Any, Dict, Optional
from urllib.parse import urlparse
from pctasks.core.storage.blob import BlobStorage

from pydantic import validator

from pctasks.core.constants import (
    DEFAULT_DATASET_TABLE_NAME,
    DEFAULT_IMAGE_KEY_TABLE_NAME,
    DEFAULT_INBOX_QUEUE_NAME,
    DEFAULT_JOB_RUN_RECORD_TABLE_NAME,
    DEFAULT_LOG_CONTAINER,
    DEFAULT_NOTIFICATIONS_QUEUE_NAME,
    DEFAULT_SIGNAL_QUEUE_NAME,
    DEFAULT_TASK_IO_CONTAINER,
    DEFAULT_TASK_RUN_RECORD_TABLE_NAME,
    DEFAULT_WORKFLOW_RUN_GROUP_RECORD_TABLE_NAME,
    DEFAULT_WORKFLOW_RUN_RECORD_TABLE_NAME,
)
from pctasks.core.models.base import PCBaseModel
from pctasks.core.models.config import QueueConnStrConfig, QueueSasConfig
from pctasks.core.settings import PCTasksSettings
from pctasks.core.tables.config import ImageKeyEntryTable
from pctasks.core.tables.dataset import DatasetIdentifierTable
from pctasks.core.tables.record import (
    JobRunRecordTable,
    TaskRunRecordTable,
    WorkflowRunGroupRecordTable,
    WorkflowRunRecordTable,
)
from pctasks.submit.settings import SubmitSettings


class BatchSettings(PCBaseModel):
    url: str
    name: Optional[str]
    key: str
    default_pool_id: str
    submit_threads: int

    def get_batch_name(self) -> str:
        return self.name or urlparse(self.url).netloc.split(".")[0]


class SignalQueueConnStrConfig(QueueConnStrConfig):
    queue_name: str = DEFAULT_SIGNAL_QUEUE_NAME

    def to_queue_config(self) -> QueueConnStrConfig:
        """Convert to a QueueSasConfig directly.

        Otherwise pydantic has trouble serializing.
        """
        return QueueConnStrConfig(
            queue_name=self.queue_name, connection_string=self.connection_string
        )


class InboxQueueConnStrConfig(QueueConnStrConfig):
    queue_name: str = DEFAULT_INBOX_QUEUE_NAME


class NotificationQueueConnStrConfig(QueueConnStrConfig):
    queue_name: str = DEFAULT_NOTIFICATIONS_QUEUE_NAME


class ExecutorSettings(PCTasksSettings):
    @classmethod
    def section_name(cls) -> str:
        return "exec"

    remote_runner_threads: int = 50
    default_task_wait_seconds: int = 60
    max_wait_retries: int = 10

    # Dev
    dev: bool = False
    local_executor_url: Optional[str] = None
    local_secrets: bool = False

    # Queues
    signal_queue: SignalQueueConnStrConfig
    signal_queue_account_name: str  # Required for generating SAS token
    signal_queue_account_key: str  # Required for generating SAS token

    inbox_queue: InboxQueueConnStrConfig
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
    batch_name: Optional[str] = None
    batch_submit_threads: int = 0

    # KeyVault
    keyvault_url: Optional[str] = None

    @property
    def batch_settings(self) -> BatchSettings:
        if not (self.batch_url and self.batch_key and self.batch_default_pool_id):
            raise ValueError("Azure Batch settings not configured")

        return BatchSettings(
            url=self.batch_url,
            name=self.batch_name,
            key=self.batch_key,
            default_pool_id=self.batch_default_pool_id,
            submit_threads=self.batch_submit_threads,
        )

    @property
    def submit_settings(self) -> SubmitSettings:
        if isinstance(self.inbox_queue, QueueSasConfig):
            return SubmitSettings(
                account_url=self.inbox_queue.account_url,
                sas_token=self.inbox_queue.sas_token,
                queue_name=self.inbox_queue.queue_name,
            )
        else:
            return SubmitSettings(
                connection_string=self.inbox_queue.connection_string,
                queue_name=self.inbox_queue.queue_name,
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
