import logging
import os
from contextlib import contextmanager
from typing import Generator, Optional

import psycopg
from psycopg.conninfo import make_conninfo
from pypgstac.db import PgstacDB
from pypgstac.migrate import Migrate

logger = logging.getLogger(__name__)

TEST_DB_NAME = "pctaskspgstactmptest"

DEV_DB_CONN_STR_ENV_VAR = "DEV_DB_CONNECTION_STRING"


@contextmanager
def temp_pgstac_db(conn_str: Optional[str] = None) -> Generator[str, None, None]:
    """Creates a temporary PgSTAC database based on an existing connection string.

    If the connection string is not provided it will be
    fetched from the DEV_DB_CONNECTION_STRING environment variable.

    Drops the database on __exit__.

    Returns the connection string to the new database.
    """
    if not conn_str:
        conn_str = os.getenv(DEV_DB_CONN_STR_ENV_VAR)

    if not conn_str:
        raise ValueError(
            f"No connection string provided and {DEV_DB_CONN_STR_ENV_VAR} is not set"
        )

    new_conn_info = make_conninfo(conn_str, dbname=TEST_DB_NAME)
    with psycopg.connect(conninfo=conn_str, autocommit=True) as conn:
        try:
            conn.execute(f"CREATE DATABASE {TEST_DB_NAME};")
        except psycopg.errors.DuplicateDatabase:
            conn.execute(f"DROP DATABASE {TEST_DB_NAME} WITH (FORCE);")
            conn.execute(f"CREATE DATABASE {TEST_DB_NAME};")

    with PgstacDB(dsn=new_conn_info) as db:
        migrator = Migrate(db)
        version = migrator.run_migration()
        print(f"Test DB migrated to version {version}")

    yield new_conn_info

    print("Dropping DB...")
    with psycopg.connect(conn_str, autocommit=True) as conn:
        conn.execute(f"DROP DATABASE {TEST_DB_NAME} WITH (FORCE);")
