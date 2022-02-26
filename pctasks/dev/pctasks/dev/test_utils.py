import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generator, List, Union

from click.testing import CliRunner, Result

from pctasks.cli.cli import pctasks_cmd
from pctasks.core.storage.base import Storage
from pctasks.core.storage.blob import BlobStorage
from pctasks.dev.constants import (
    AZURITE_ACCOUNT_KEY,
    AZURITE_HOST_ENV_VAR,
    TEST_DATA_CONTAINER,
)
from pctasks.execute.settings import ExecutorSettings


class CliTestError(Exception):
    pass


def get_azurite_test_storage() -> BlobStorage:
    account_name = "devstoreaccount1"
    settings = ExecutorSettings.get()
    if settings.blob_account_name == account_name:
        account_url = settings.blob_account_url
    else:
        hostname = os.getenv(AZURITE_HOST_ENV_VAR, None)
        if not hostname:
            raise Exception(
                "Can not determine Azurite hostname. "
                f" Please set the '{AZURITE_HOST_ENV_VAR}' environment variable."
            )
        account_url = f"http://{hostname}:10000/devstoreaccount1"

    return BlobStorage.from_account_key(
        account_key=AZURITE_ACCOUNT_KEY,
        account_url=account_url,
        blob_uri=f"blob://{account_name}/{TEST_DATA_CONTAINER}",
    )


def run_pctasks(cmd: List[Any], catch_exceptions: bool = False) -> Result:
    runner = CliRunner()

    if len(cmd) == 0:
        raise Exception("Empty command")

    result = runner.invoke(pctasks_cmd, [str(c) for c in cmd], catch_exceptions=True)
    if result.output:
        print(result.output)
    if result.exception is not None and not catch_exceptions:
        raise CliTestError("Test code threw an exception") from result.exception
    return result


@contextmanager
def environment(**kwargs: str) -> Generator[None, None, None]:
    """Temporarily set environment variables inside the context manager and
    fully restore previous environment afterwards

    https://gist.github.com/igniteflow/7267431
    """
    original_env = {key: os.getenv(key) for key in kwargs}
    os.environ.update(kwargs)
    try:
        yield
    finally:
        for key, value in original_env.items():
            if value is None:
                del os.environ[key]
            else:
                os.environ[key] = value


@contextmanager
def files_in_azurite(directory: Union[str, Path]) -> Generator[Storage, None, None]:
    storage = get_azurite_test_storage()
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
