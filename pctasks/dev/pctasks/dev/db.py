import logging
import os
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterator, Optional

import psycopg
from psycopg.conninfo import make_conninfo
from pypgstac.db import PgstacDB
from pypgstac.migrate import Migrate

logger = logging.getLogger(__name__)

TEST_DB_NAME = "pctaskspgstactmptest"

DEV_DB_CONN_STR_ENV_VAR = "DEV_DB_CONNECTION_STRING"
DEV_REMOTE_DB_CONN_STR_ENV_VAR = "DEV_REMOTE_DB_CONNECTION_STRING"


@dataclass
class ConnStrInfo:
    local: str
    """Connection string that can be accessed by the process running tests"""

    remote: str
    """Connection string that can be accessed by tasks running on the remote server

    This may be different if for instance the test accessing the database through
    localhost and the task is accessing through the docker network.

    Will be the same as local DEV_REMOTE_DB_CONNECTION_STRING is not provided.
    """


@contextmanager
def temp_pgstac_db(
    conn_str: Optional[str] = None,
) -> Iterator[ConnStrInfo]:
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

    remote_conn_str = os.getenv(DEV_REMOTE_DB_CONN_STR_ENV_VAR)
    if remote_conn_str:
        new_remote_conn_info = make_conninfo(remote_conn_str, dbname=TEST_DB_NAME)
    else:
        new_remote_conn_info = new_conn_info
    try:
        yield ConnStrInfo(local=new_conn_info, remote=new_remote_conn_info)
    finally:
        print("Dropping DB...")
        with psycopg.connect(conn_str, autocommit=True) as conn:
            conn.execute(f"DROP DATABASE {TEST_DB_NAME} WITH (FORCE);")
