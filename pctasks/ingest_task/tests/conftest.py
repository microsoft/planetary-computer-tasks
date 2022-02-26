import os
from contextlib import contextmanager
from typing import Generator

from pctasks.dev.test_utils import environment
from pctasks.ingest_task.constants import DB_CONNECTION_STRING_ENV_VALUE


@contextmanager
def ingest_test_environment() -> Generator[None, None, None]:
    db_secret = os.getenv("SECRETS_DB_CONNECTION_STRING")

    if not db_secret:
        raise ValueError("SECRETS_DB_CONNECTION_STRING must be set")

    with environment(**{DB_CONNECTION_STRING_ENV_VALUE: db_secret}):
        print("one")
        yield
        print("two")
