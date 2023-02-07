import os
from contextlib import contextmanager
from typing import Generator

from pctasks.core.utils import environment
from pctasks.dev.db import ConnStrInfo, temp_pgstac_db
from pctasks.ingest.constants import DB_CONNECTION_STRING_ENV_VAR


@contextmanager
def ingest_test_environment() -> Generator[ConnStrInfo, None, None]:
    db_secret = os.getenv("SECRETS_DB_CONNECTION_STRING")
    # Why doesn't this set it automatically?
    # Why doesn't this use DEV_DB_CONNECTION_STRING?

    if not db_secret:
        raise ValueError("SECRETS_DB_CONNECTION_STRING must be set")

    with temp_pgstac_db(db_secret) as test_db_conn_str:
        with environment(**{DB_CONNECTION_STRING_ENV_VAR: test_db_conn_str.local}):
            yield test_db_conn_str
