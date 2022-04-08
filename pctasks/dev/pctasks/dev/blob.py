import os
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Generator, List, Optional, Union

from azure.storage.blob import ContainerSasPermissions, generate_container_sas

from pctasks.core.storage.base import Storage
from pctasks.core.storage.blob import BlobStorage
from pctasks.dev.constants import (
    AZURITE_ACCOUNT_KEY,
    AZURITE_ACCOUNT_NAME,
    AZURITE_HOST_ENV_VAR,
    TEST_DATA_CONTAINER,
)
from pctasks.execute.settings import ExecutorSettings


def get_azurite_test_storage() -> BlobStorage:
    account_name = AZURITE_ACCOUNT_NAME
    executor_settings: Optional[ExecutorSettings] = None
    try:
        executor_settings = ExecutorSettings.get()
    except Exception:
        # Don't fail for environments that don't have executor settings set
        pass
    if executor_settings and executor_settings.blob_account_name == account_name:
        account_url = executor_settings.blob_account_url
    else:
        hostname = os.getenv(AZURITE_HOST_ENV_VAR, "localhost")
        account_url = f"http://{hostname}:10000/devstoreaccount1"

    return BlobStorage.from_account_key(
        account_key=AZURITE_ACCOUNT_KEY,
        account_url=account_url,
        blob_uri=f"blob://{account_name}/{TEST_DATA_CONTAINER}",
    )


def get_azurite_sas_token() -> str:
    return generate_container_sas(
        account_name=AZURITE_ACCOUNT_NAME,
        account_key=AZURITE_ACCOUNT_KEY,
        container_name=TEST_DATA_CONTAINER,
        start=datetime.now(),
        expiry=datetime.utcnow() + timedelta(hours=24 * 7),
        permission=ContainerSasPermissions(
            read=True, list=True, write=True, delete=True
        ),
    )


@contextmanager
def files_in_azurite(directory: Union[str, Path]) -> Generator[Storage, None, None]:
    storage = get_azurite_test_storage()
    for x in storage.list_files():
        print(x)
    sub_storage = storage.get_substorage("test")
    d = Path(directory)
    paths_to_delete: List[str] = []
    for root, _, files in os.walk(d):
        for f in files:
            file_path = os.path.join(root, f)
            rel_path = os.path.relpath(file_path, d)
            sub_storage.upload_file(file_path, rel_path)
            paths_to_delete.append(rel_path)
    try:
        yield sub_storage
    finally:
        for path in paths_to_delete:
            sub_storage.delete_file(path)
