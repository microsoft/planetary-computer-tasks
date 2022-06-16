from datetime import datetime, timedelta

from azure.core.credentials import AzureNamedKeyCredential
from azure.data.tables import TableSasPermissions, generate_table_sas
from azure.storage.blob import BlobSasPermissions, generate_blob_sas

from pctasks.core.models.config import BlobConfig, TableSasConfig
from pctasks.run.settings import RunSettings


def get_table_config(name: str, permissions: str = "rwuadl") -> TableSasConfig:
    exec_settings = RunSettings.get()

    tables_cred = AzureNamedKeyCredential(
        name=exec_settings.tables_account_name,
        key=exec_settings.tables_account_key,
    )

    tasks_table_sas_token = generate_table_sas(
        credential=tables_cred,
        table_name=name,
        start=datetime.now(),
        expiry=datetime.utcnow() + timedelta(hours=24 * 7),
        permission=TableSasPermissions(
            read="r" in permissions,
            write="w" in permissions,
            update="u" in permissions,
            add="a" in permissions,
            delete="d" in permissions,
            list="l" in permissions,
        ),
    )

    return TableSasConfig(
        account_url=exec_settings.tables_account_url,
        table_name=name,
        sas_token=tasks_table_sas_token,
    )


def get_blob_config(container: str, path: str) -> BlobConfig:
    exec_settings = RunSettings.get()

    blob_uri = f"blob://{exec_settings.blob_account_name}" f"/{container}/{path}"

    blob_sas_token = generate_blob_sas(
        account_name=exec_settings.blob_account_name,
        account_key=exec_settings.blob_account_key,
        container_name=container,
        blob_name=path,
        start=datetime.now(),
        expiry=datetime.utcnow() + timedelta(hours=24 * 7),
        permission=BlobSasPermissions(write=True),
    )

    return BlobConfig(
        uri=blob_uri,
        sas_token=blob_sas_token,
        account_url=exec_settings.blob_account_url,
    )
