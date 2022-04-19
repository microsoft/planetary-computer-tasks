import os
from contextlib import contextmanager, asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Generator, Optional, Union
from uuid import uuid1

from azure.storage.blob import ContainerSasPermissions, generate_container_sas

from pctasks.core.storage.base import Storage
from pctasks.core.storage.blob import BlobStorage
from pctasks.core.storage.async_blob import AsyncBlobStorage
from pctasks.dev.constants import (
    AZURITE_ACCOUNT_KEY,
    AZURITE_ACCOUNT_NAME,
    AZURITE_HOST_ENV_VAR,
    TEST_DATA_CONTAINER,
)
from pctasks.execute.settings import ExecutorSettings


def get_azurite_test_storage(sync=True) -> BlobStorage:
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

    cls = BlobStorage if sync else AsyncBlobStorage

    return cls.from_account_key(
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


def copy_dir_to_azurite(
    storage: Storage, directory: Union[str, Path], prefix: Optional[str] = None
) -> None:
    if prefix:
        storage = storage.get_substorage(prefix)

    for root, _, files in os.walk(directory):
        for f in files:
            file_path = os.path.join(root, f)
            rel_path = os.path.relpath(file_path, directory)
            storage.upload_file(file_path, rel_path)

async def async_copy_dir_to_azurite(
    storage: Storage, directory: Union[str, Path], prefix: Optional[str] = None
) -> None:
    if prefix:
        storage = storage.get_substorage(prefix)

    for root, _, files in os.walk(directory):
        for f in files:
            file_path = os.path.join(root, f)
            rel_path = os.path.relpath(file_path, directory)
            await storage.upload_file(file_path, rel_path)


@contextmanager
def temp_azurite_blob_storage(
    test_files: Optional[Union[str, Path]] = None,
) -> Generator[Storage, None, None]:
    storage = get_azurite_test_storage()
    sub_storage = storage.get_substorage(f"test-{uuid1().hex}")
    if test_files:
        copy_dir_to_azurite(sub_storage, test_files)
    try:
        yield sub_storage
    finally:
        # for path in sub_storage.list_files():
        #     sub_storage.delete_file(path)
        pass


@asynccontextmanager
async def async_temp_azurite_blob_storage(
    test_files: Optional[Union[str, Path]] = None,
) -> Generator[Storage, None, None]:
    storage = get_azurite_test_storage(sync=False)
    sub_storage = storage.get_substorage(f"test-{uuid1().hex}")
    if test_files:
        await async_copy_dir_to_azurite(sub_storage, test_files)
    try:
        yield sub_storage
    finally:
        # for path in sub_storage.list_files():
        #     sub_storage.delete_file(path)
        pass
