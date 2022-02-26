from datetime import datetime, timedelta

from azure.storage.blob import ContainerSasPermissions, generate_container_sas

from pctasks.core.constants import DEFAULT_LOG_CONTAINER
from pctasks.core.storage.blob import BlobStorage
from pctasks.dev.env import (
    PCTASKS_BLOB_ACCOUNT_KEY_ENV_VAR,
    PCTASKS_BLOB_ACCOUNT_NAME_ENV_VAR,
    PCTASKS_BLOB_ACCOUNT_URL_ENV_VAR,
    get_dev_env,
)


def get_log_storage(container: str = DEFAULT_LOG_CONTAINER) -> BlobStorage:
    account_name = get_dev_env(PCTASKS_BLOB_ACCOUNT_NAME_ENV_VAR)
    log_blob_sas_token = generate_container_sas(
        account_name=account_name,
        account_key=get_dev_env(PCTASKS_BLOB_ACCOUNT_KEY_ENV_VAR),
        container_name=container,
        start=datetime.now(),
        expiry=datetime.utcnow() + timedelta(hours=24 * 7),
        permission=ContainerSasPermissions(read=True, write=True, delete=True),
    )

    return BlobStorage.from_uri(
        blob_uri=f"blob://{account_name}/{container}",
        sas_token=log_blob_sas_token,
        account_url=get_dev_env(PCTASKS_BLOB_ACCOUNT_URL_ENV_VAR),
    )
