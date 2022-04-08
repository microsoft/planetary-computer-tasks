import os
from contextlib import contextmanager
from typing import Generator

import psycopg
import pytest
from pypgstac.db import PgstacDB
from pypgstac.load import Loader
from pypgstac.migrate import Migrate

from pctasks.core.utils import environment
from pctasks.ingest_task.constants import DB_CONNECTION_STRING_ENV_VALUE


@contextmanager
def ingest_test_environment() -> Generator[None, None, None]:
    db_secret = os.getenv("SECRETS_DB_CONNECTION_STRING")

    if not db_secret:
        raise ValueError("SECRETS_DB_CONNECTION_STRING must be set")

    with environment(**{DB_CONNECTION_STRING_ENV_VALUE: db_secret}):
        yield


@pytest.fixture(scope="function")
def db() -> Generator:
    """Fixture to get a fresh database."""
    origdb: str = os.getenv("PGDATABASE", "")

    with psycopg.connect(autocommit=True) as conn:
        try:
            conn.execute("CREATE DATABASE pgstactestdb;")
        except psycopg.errors.DuplicateDatabase:
            conn.execute("DROP DATABASE pgstactestdb WITH (FORCE);")
            conn.execute("CREATE DATABASE pgstactestdb;")

    os.environ["PGDATABASE"] = "pgstactestdb"

    pgdb = PgstacDB()

    yield pgdb

    print("Closing Connection and Dropping DB")
    pgdb.close()
    os.environ["PGDATABASE"] = origdb

    with psycopg.connect(autocommit=True) as conn:
        conn.execute("DROP DATABASE pgstactestdb WITH (FORCE);")


@pytest.fixture(scope="function")
def loader(db: PgstacDB) -> Generator:
    """Fixture to get a loader and an empty pgstac."""
    db.query("DROP SCHEMA IF EXISTS pgstac CASCADE;")
    migrator = Migrate(db)
    print(migrator.run_migration())
    ldr = Loader(db)
    yield ldr
