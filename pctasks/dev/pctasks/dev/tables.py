from datetime import datetime, timedelta
from typing import Any, Optional
from uuid import uuid1

from azure.core.credentials import AzureNamedKeyCredential
from azure.data.tables import (
    AccountSasPermissions,
    ResourceTypes,
    TableClient,
    TableServiceClient,
    generate_account_sas,
)

from pctasks.core.constants import (
    DEFAULT_JOB_RUN_RECORD_TABLE_NAME,
    DEFAULT_TASK_RUN_RECORD_TABLE_NAME,
    DEFAULT_WORKFLOW_RUN_RECORD_TABLE_NAME,
)
from pctasks.core.tables.base import AzureSasCredential
from pctasks.core.tables.record import (
    JobRunRecordTable,
    TaskRunRecordTable,
    WorkflowRunRecordTable,
)
from pctasks.dev.config import get_table_config
from pctasks.execute.settings import ExecutorSettings

exec_settings = ExecutorSettings.get()


def get_task_run_record_table() -> TaskRunRecordTable:
    return TaskRunRecordTable.from_account_key(
        account_url=exec_settings.tables_account_url,
        account_name=exec_settings.tables_account_name,
        account_key=exec_settings.tables_account_key,
        table_name=DEFAULT_TASK_RUN_RECORD_TABLE_NAME,
    )


def get_job_run_record_table() -> JobRunRecordTable:
    return JobRunRecordTable.from_account_key(
        account_url=exec_settings.tables_account_url,
        account_name=exec_settings.tables_account_name,
        account_key=exec_settings.tables_account_key,
        table_name=DEFAULT_JOB_RUN_RECORD_TABLE_NAME,
    )


def get_workflow_run_record_table() -> WorkflowRunRecordTable:
    return WorkflowRunRecordTable.from_account_key(
        account_url=exec_settings.tables_account_url,
        account_name=exec_settings.tables_account_name,
        account_key=exec_settings.tables_account_key,
        table_name=DEFAULT_WORKFLOW_RUN_RECORD_TABLE_NAME,
    )


class TempTable:
    def __init__(self, permissions: str = "rwuad") -> None:
        account_name = exec_settings.tables_account_name
        account_key = exec_settings.tables_account_key

        self.table_config = get_table_config(
            name=f"testtable{uuid1().hex}", permissions=permissions
        )

        self._tables_cred = AzureNamedKeyCredential(name=account_name, key=account_key)

        self._account_sas = AzureSasCredential(
            generate_account_sas(
                start=datetime.now(),
                expiry=datetime.utcnow() + timedelta(hours=24 * 7),
                credential=self._tables_cred,
                resource_types=ResourceTypes(service=True, container=True, object=True),
                permission=AccountSasPermissions(
                    create=True,
                    add=True,
                    update=True,
                    process=True,
                    delete=True,
                    list=True,
                ),
            )
        )

        self._service_client: Optional[TableServiceClient] = None
        self._table_client: Optional[TableClient] = None

    def __enter__(self) -> TableClient:
        self._service_client = TableServiceClient(
            endpoint=self.table_config.account_url, credential=self._tables_cred
        )

        self._service_client.create_table(self.table_config.table_name)

        self._table_client = TableServiceClient(
            endpoint=self.table_config.account_url,
            credential=AzureSasCredential(self.table_config.sas_token),
        ).get_table_client(self.table_config.table_name)

        return self._table_client

    def __exit__(self, *args: Any) -> None:
        if self._table_client:
            self._table_client.close()
            self._table_client = None
        if self._service_client:
            self._service_client.delete_table(self.table_config.table_name)
            self._service_client.close()
            self._service_client = None
