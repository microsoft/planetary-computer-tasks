import logging
from contextlib import contextmanager
from typing import Generator

import psycopg
from psycopg.conninfo import make_conninfo
from pypgstac.db import PgstacDB
from pypgstac.migrate import Migrate

logger = logging.getLogger(__name__)

TEST_DB_NAME = "pctaskspgstactmptest"


@contextmanager
def test_pgstac_db(conn_str: str) -> Generator[str, None, None]:
    """Creates a temporary PgSTAC database based on an existing connection string.

    Drops the database on __exit__.

    Returns the connection string to the new database.
    """
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
