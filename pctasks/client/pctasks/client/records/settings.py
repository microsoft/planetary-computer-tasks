# from typing import Optional

# from cachetools import Cache, LRUCache, cachedmethod

# from pctasks.core.constants import (
#     DEFAULT_DATASET_TABLE_NAME,
#     DEFAULT_JOB_RUN_RECORD_TABLE_NAME,
#     DEFAULT_TASK_RUN_RECORD_TABLE_NAME,
#     DEFAULT_WORKFLOW_RUN_GROUP_RECORD_TABLE_NAME,
#     DEFAULT_WORKFLOW_RUN_RECORD_TABLE_NAME,
# )
# from pctasks.core.models.base import PCBaseModel
# from pctasks.core.settings import PCTasksSettings
# from pctasks.core.tables.dataset import DatasetIdentifierTable
# from pctasks.core.tables.record import (
#     JobRunRecordTable,
#     TaskRunRecordTable,
#     WorkflowRunGroupRecordTable,
#     WorkflowRunRecordTable,
# )


# class TablesConfig(PCBaseModel):
#     """Configuration for accessing tables.

#     This is a temporary solution until we can fit
#     a REST API in front of PCTasks.
#     """

#     _cache: Cache = LRUCache(maxsize=100)

#     connection_string: str
#     dataset_table_name: str = DEFAULT_DATASET_TABLE_NAME
#     task_run_record_table_name: str = DEFAULT_TASK_RUN_RECORD_TABLE_NAME
#     job_run_record_table_name: str = DEFAULT_JOB_RUN_RECORD_TABLE_NAME
#     workflow_run_record_table_name: str = DEFAULT_WORKFLOW_RUN_RECORD_TABLE_NAME
#     workflow_run_group_record_table_name: str = (
#         DEFAULT_WORKFLOW_RUN_GROUP_RECORD_TABLE_NAME
#     )

#     @cachedmethod(lambda self: self._cache, key=lambda self: self.dataset_table_name)
#     def get_dataset_table(self) -> DatasetIdentifierTable:
#         return DatasetIdentifierTable.from_connection_string(
#             connection_string=self.connection_string,
#             table_name=self.dataset_table_name,
#         )

#     @cachedmethod(
#         lambda self: self._cache, key=lambda self: self.task_run_record_table_name
#     )
#     def get_task_run_record_table(self) -> TaskRunRecordTable:
#         return TaskRunRecordTable.from_connection_string(
#             connection_string=self.connection_string,
#             table_name=self.task_run_record_table_name,
#         )

#     @cachedmethod(
#         lambda self: self._cache, key=lambda self: self.job_run_record_table_name
#     )
#     def get_job_run_record_table(self) -> JobRunRecordTable:
#         return JobRunRecordTable.from_connection_string(
#             connection_string=self.connection_string,
#             table_name=self.job_run_record_table_name,
#         )

#     @cachedmethod(
#         lambda self: self._cache, key=lambda self: self.workflow_run_record_table_name
#     )
#     def get_workflow_run_record_table(self) -> WorkflowRunRecordTable:
#         return WorkflowRunRecordTable.from_connection_string(
#             connection_string=self.connection_string,
#             table_name=self.workflow_run_record_table_name,
#         )

#     @cachedmethod(
#         lambda self: self._cache,
#         key=lambda self: self.workflow_run_group_record_table_name,
#     )
#     def get_workflow_run_group_record_table(self) -> WorkflowRunGroupRecordTable:
#         return WorkflowRunGroupRecordTable.from_connection_string(
#             connection_string=self.connection_string,
#             table_name=self.workflow_run_group_record_table_name,
#         )


# class RecordsSettings(PCTasksSettings):
#     @classmethod
#     def section_name(cls) -> str:
#         return "records"

#     tables: TablesConfig
#     app_insights_workspace_id: Optional[str] = None

#     # Settings for fetching logs.

#     logs_sas_token: Optional[str] = None
#     logs_account_url: Optional[str] = None
#     logs_account_key: Optional[str] = None
