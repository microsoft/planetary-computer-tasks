import os
from contextlib import contextmanager
from typing import Generator

from pctasks.core.utils import environment
from pctasks.dev.db import test_pgstac_db
from pctasks.ingest.constants import DB_CONNECTION_STRING_ENV_VALUE


@contextmanager
def ingest_test_environment() -> Generator[None, None, None]:
    db_secret = os.getenv("SECRETS_DB_CONNECTION_STRING")

    if not db_secret:
        raise ValueError("SECRETS_DB_CONNECTION_STRING must be set")

    with test_pgstac_db(db_secret) as test_db_conn_str:
        with environment(**{DB_CONNECTION_STRING_ENV_VALUE: test_db_conn_str}):
            yield
