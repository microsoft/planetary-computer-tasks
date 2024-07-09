from datetime import datetime, timedelta
from typing import Optional

from azure.core.credentials import AzureNamedKeyCredential
from azure.data.tables import TableSasPermissions, generate_table_sas
from azure.storage.blob import BlobSasPermissions, generate_blob_sas

from pctasks.core.models.config import BlobConfig, TableSasConfig
from pctasks.dev.blob import get_azurite_account_url
from pctasks.dev.constants import AZURITE_ACCOUNT_KEY, AZURITE_ACCOUNT_NAME
from pctasks.run.settings import RunSettings


def get_table_config(name: str, permissions: str = "rwuadl") -> TableSasConfig:
    run_settings = RunSettings.get()

    assert run_settings.tables_account_key is not None  # for mypy
    tables_cred = AzureNamedKeyCredential(
        name=run_settings.tables_account_name,
        key=run_settings.tables_account_key,
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
        account_url=run_settings.tables_account_url,
        table_name=name,
        sas_token=tasks_table_sas_token,
    )


def get_blob_config(
    container: str, path: str, account_name: Optional[str] = None
) -> BlobConfig:
    run_settings = RunSettings.get()

    blob_uri = f"blob://{run_settings.blob_account_name}/{container}/{path}"

    blob_sas_token = generate_blob_sas(
        account_name=run_settings.blob_account_name,
        account_key=run_settings.blob_account_key,
        container_name=container,
        blob_name=path,
        start=datetime.utcnow(),
        expiry=datetime.utcnow() + timedelta(hours=24 * 7),
        permission=BlobSasPermissions(write=True),
    )

    return BlobConfig(
        uri=blob_uri,
        sas_token=blob_sas_token,
        account_url=run_settings.blob_account_url,
    )


def get_azurite_blob_config(container: str, path: str) -> BlobConfig:
    blob_uri = f"blob://{AZURITE_ACCOUNT_NAME}/{container}/{path}"

    blob_sas_token = generate_blob_sas(
        account_name=AZURITE_ACCOUNT_NAME,
        account_key=AZURITE_ACCOUNT_KEY,
        container_name=container,
        blob_name=path,
        start=datetime.utcnow(),
        expiry=datetime.utcnow() + timedelta(hours=24 * 7),
        permission=BlobSasPermissions(write=True),
    )

    return BlobConfig(
        uri=blob_uri,
        sas_token=blob_sas_token,
        account_url=get_azurite_account_url(),
    )
