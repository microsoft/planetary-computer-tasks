from typing import Any, Dict, Optional

from cachetools import Cache, LRUCache, cachedmethod
from pydantic import Field, validator

from pctasks.core.constants import (
    DEFAULT_DATASET_TABLE_NAME,
    DEFAULT_JOB_RUN_RECORD_TABLE_NAME,
    DEFAULT_TASK_RUN_RECORD_TABLE_NAME,
    DEFAULT_WORKFLOW_RUN_RECORD_TABLE_NAME,
)
from pctasks.core.models.base import PCBaseModel
from pctasks.core.settings import PCTasksSettings
from pctasks.core.tables.dataset import DatasetIdentifierTable
from pctasks.core.tables.record import (
    JobRunRecordTable,
    TaskRunRecordTable,
    WorkflowRunRecordTable,
)

APP_INSIGHTS_INSTRUMENTATION_KEY_ENV_VAR = "APP_INSIGHTS_INSTRUMENTATION_KEY"


class RecordTablesConfig(PCBaseModel):
    """Configuration for accessing tables for records."""

    _cache: Cache = LRUCache(maxsize=100)

    connection_string: str
    dataset_table_name: str = DEFAULT_DATASET_TABLE_NAME
    task_run_record_table_name: str = DEFAULT_TASK_RUN_RECORD_TABLE_NAME
    job_run_record_table_name: str = DEFAULT_JOB_RUN_RECORD_TABLE_NAME
    workflow_run_record_table_name: str = DEFAULT_WORKFLOW_RUN_RECORD_TABLE_NAME

    @cachedmethod(lambda self: self._cache, key=lambda self: self.dataset_table_name)
    def get_dataset_table(self) -> DatasetIdentifierTable:
        return DatasetIdentifierTable.from_connection_string(
            connection_string=self.connection_string,
            table_name=self.dataset_table_name,
        )

    @cachedmethod(
        lambda self: self._cache, key=lambda self: self.task_run_record_table_name
    )
    def get_task_run_record_table(self) -> TaskRunRecordTable:
        return TaskRunRecordTable.from_connection_string(
            connection_string=self.connection_string,
            table_name=self.task_run_record_table_name,
        )

    @cachedmethod(
        lambda self: self._cache, key=lambda self: self.job_run_record_table_name
    )
    def get_job_run_record_table(self) -> JobRunRecordTable:
        return JobRunRecordTable.from_connection_string(
            connection_string=self.connection_string,
            table_name=self.job_run_record_table_name,
        )

    @cachedmethod(
        lambda self: self._cache, key=lambda self: self.workflow_run_record_table_name
    )
    def get_workflow_run_record_table(self) -> WorkflowRunRecordTable:
        return WorkflowRunRecordTable.from_connection_string(
            connection_string=self.connection_string,
            table_name=self.workflow_run_record_table_name,
        )


class ServerSettings(PCTasksSettings):
    @classmethod
    def section_name(cls) -> str:
        return "server"

    dev: bool = False
    dev_api_key: Optional[str] = None
    dev_auth_token: Optional[str] = None

    access_key: Optional[str] = None

    record_tables: RecordTablesConfig

    app_insights_instrumentation_key: Optional[str] = Field(
        default=None,
        env=APP_INSIGHTS_INSTRUMENTATION_KEY_ENV_VAR,
    )

    @validator("dev_api_key", always=True)
    def _dev_api_key_validator(
        cls, v: Optional[str], values: Dict[str, Any]
    ) -> Optional[str]:
        if values.get("dev"):
            if not v:
                raise ValueError("dev_api_key is required when dev is True")
        return v

    @validator("dev_auth_token", always=True)
    def _dev_auth_token_validator(
        cls, v: Optional[str], values: Dict[str, Any]
    ) -> Optional[str]:
        if values.get("dev"):
            if not v:
                raise ValueError("dev_auth_token is required when dev is True")
        return v
