from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional, Union
from urllib.parse import urlparse

from pydantic import Field, validator

from pctasks.core.constants import (
    DEFAULT_CODE_CONTAINER,
    DEFAULT_IMAGE_KEY_TABLE_NAME,
    DEFAULT_LOG_CONTAINER,
    DEFAULT_NOTIFICATIONS_QUEUE_NAME,
    DEFAULT_TASK_IO_CONTAINER,
)
from pctasks.core.cosmos.database import CosmosDBDatabase
from pctasks.core.cosmos.settings import CosmosDBSettings
from pctasks.core.models.base import PCBaseModel
from pctasks.core.models.config import QueueConnStrConfig
from pctasks.core.settings import PCTasksSettings
from pctasks.core.storage.blob import BlobStorage
from pctasks.core.tables.config import ImageKeyEntryTable


class TaskRunnerType(str, Enum):
    ARGO = "argo"
    BATCH = "batch"
    LOCAL = "local"


class WorkflowRunnerType(str, Enum):
    ARGO = "argo"
    LOCAL = "local"


class BatchSettings(PCBaseModel):
    url: str
    key: str
    default_pool_id: str
    submit_threads: int
    cache_seconds: int = 5  # How long to cache batch API responses

    def get_batch_name(self) -> str:
        return urlparse(self.url).netloc.split(".")[0]


class NotificationQueueConnStrConfig(QueueConnStrConfig):
    queue_name: str = Field(DEFAULT_NOTIFICATIONS_QUEUE_NAME)


class RunSettings(PCTasksSettings):
    @classmethod
    def section_name(cls) -> str:
        return "run"

    max_concurrent_workflow_tasks: int = 120
    remote_runner_threads: int = 50
    default_task_wait_seconds: int = 60
    max_wait_retries: int = 10
    task_poll_seconds: int = 30
    check_output_seconds: int = 3
    check_status_blob_seconds: int = 5

    # Dev
    local_dev_endpoints_url: Optional[str] = None
    local_secrets: bool = False

    notification_queue: NotificationQueueConnStrConfig = Field()

    # Tables
    tables_account_url: str
    tables_account_name: str
    tables_account_key: Optional[str]
    image_key_table_name: str = DEFAULT_IMAGE_KEY_TABLE_NAME

    # Blob
    blob_account_url: str
    blob_account_name: str
    blob_account_key: Optional[str]
    log_blob_container: str = DEFAULT_LOG_CONTAINER
    task_io_blob_container: str = DEFAULT_TASK_IO_CONTAINER
    code_blob_container: str = DEFAULT_CODE_CONTAINER

    # Batch
    batch_url: Optional[str] = None
    batch_key: Optional[str] = None
    batch_default_pool_id: Optional[str] = None
    batch_submit_threads: int = 0
    batch_cache_seconds: int = 5  # How long to cache batch API responses

    # Argo
    argo_host: Optional[str] = None
    argo_token: Optional[str] = None
    argo_namespace: str = "argo"
    argo_node_group: Optional[str] = None
    workflow_runner_image: Optional[str] = None

    task_service_account_name: Optional[str] = None
    task_workload_identity_client_id: Optional[str] = None
    task_workload_identity_tenant_id: Optional[str] = None

    # KeyVault
    keyvault_url: Optional[str] = None
    keyvault_sp_tenant_id: Optional[str] = None
    keyvault_sp_client_id: Optional[str] = None
    keyvault_sp_client_secret: Optional[str] = None

    # Streaming task IO service principal
    # If set, will be used by the task
    # to read and write to the task IO and log container
    # instead of using SAS Tokens.
    streaming_taskio_sp_tenant_id: Optional[str] = None
    streaming_taskio_sp_client_id: Optional[str] = None
    streaming_taskio_sp_client_secret: Optional[str] = None

    streaming_task_namespace: str = "tasks"
    streaming_task_node_group: Optional[str] = None

    # Type of task runner to use.
    task_runner_type: TaskRunnerType = TaskRunnerType.BATCH

    # Type of workflow runner to use.
    workflow_runner_type: WorkflowRunnerType = WorkflowRunnerType.ARGO

    applicationinsights_connection_string: Optional[str] = None

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
            if values.get("local_dev_endpoints_url") is None:
                raise ValueError(
                    "Must specify local_dev_endpoints_url for local remote runner type."
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

    @validator("workflow_runner_type", always=True)
    def _workflow_runner_type_validator(
        cls, v: WorkflowRunnerType, values: Dict[str, Any]
    ) -> WorkflowRunnerType:
        if v == WorkflowRunnerType.ARGO:
            if values.get("argo_host") is None:
                raise ValueError(
                    "Must specify argo_host for argo workflow runner type."
                )
            if values.get("argo_token") is None:
                raise ValueError(
                    "Must specify argo_token for argo workflow runner type."
                )
            if values.get("workflow_runner_image") is None:
                raise ValueError(
                    "Must specify workflow_runner_image "
                    "for argo workflow runner type."
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

    def get_code_storage(self) -> BlobStorage:
        return BlobStorage.from_account_key(
            f"blob://{self.blob_account_name}/{self.code_blob_container}",
            account_key=self.blob_account_key,
            account_url=self.blob_account_url,
        )


class WorkflowExecutorConfig(PCBaseModel):
    run_settings: RunSettings
    cosmosdb_settings: CosmosDBSettings

    def get_cosmosdb(self) -> CosmosDBDatabase:
        return CosmosDBDatabase(settings=self.cosmosdb_settings)

    @classmethod
    def get(
        cls,
        profile: Optional[str] = None,
        settings_file: Optional[Union[str, Path]] = None,
    ) -> "WorkflowExecutorConfig":
        run_settings = RunSettings.get(profile, settings_file)
        cosmosdb_settings = CosmosDBSettings.get(profile, settings_file)
        return cls(run_settings=run_settings, cosmosdb_settings=cosmosdb_settings)
