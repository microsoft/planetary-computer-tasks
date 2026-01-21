import logging
import os
from typing import Any, Callable, Dict, Iterable, Optional, Set, TypeVar

import orjson
import psycopg
from pypgstac.db import PgstacDB
from pypgstac.load import Loader, Methods

from pctasks.core.utils import grouped

logger = logging.getLogger(__name__)

T = TypeVar("T")


class PgSTAC:
    db: PgstacDB

    def __init__(self, pg_connection_string: str) -> None:
        self.db = PgstacDB(pg_connection_string, debug=True)
        # self.db.connect()
        self.loader = Loader(self.db)

    def _with_connection_retry(self, func: Callable[[], T], retries: int = 0) -> T:
        """Tries a function against the DB, retires on connection timeout."""
        MAX_RETRIES = 1
        try:
            return func()
        except psycopg.OperationalError as e:
            if "connection" in str(e).lower():
                logger.warning(f"  ...Connection broken; retrying connection: {e}")
                if retries >= MAX_RETRIES:
                    raise
                self.db.disconnect()
                self.db.connect()
                return self._with_connection_retry(func, retries + 1)
            else:
                raise

    def unique_items(
        self, items: Iterable[bytes], key_func: Callable[[bytes], Any]
    ) -> Iterable[bytes]:
        seen = set()
        for item in items:
            k = key_func(item)
            if k not in seen:
                seen.add(k)
                yield item

    def ingest_items(
        self,
        items: Iterable[bytes],
        mode: Methods = Methods.upsert,
        insert_group_size: Optional[int] = None,
    ) -> None:
        all_unique_items = list(
            self.unique_items(items, lambda b: orjson.loads(b)["id"])
        )
        if insert_group_size:
            groups = grouped(all_unique_items, insert_group_size)
        else:
            groups = [all_unique_items]

        for i, group in enumerate(groups):
            logger.info(f"  ...Loading group {i + 1}")
            self._with_connection_retry(
                lambda: self.loader.load_items(
                    iter(group),
                    insert_mode=mode,
                )
            )

    def ingest_collections(
        self,
        collections: Iterable[Dict[str, Any]],
        mode: Methods = Methods.upsert,
    ) -> None:
        self._with_connection_retry(
            lambda: self.loader.load_collections(
                iter(
                    [
                        orjson.dumps(c, option=orjson.OPT_SERIALIZE_NUMPY)
                        for c in collections
                    ]
                ),
                insert_mode=mode,
            )
        )

    def existing_items(self, collection_id: str, item_ids: Set[str]) -> Set[str]:
        """The IDs of Items that already exist in the database."""
        rows = self._with_connection_retry(
            lambda: self.db.query(
                """
                SELECT id from items where id = ANY(%s) and collection = %s
            """,
                args=[list(item_ids), collection_id],
            )
        )
        return set([row[0] for row in rows])

    def collection_exists(self, collection_id: str) -> bool:
        rows = self._with_connection_retry(
            lambda: self.db.query(
                """
                SELECT id from collections where id = %s
            """,
                args=[collection_id],
            )
        )

        return any(rows)

    @classmethod
    def from_env(cls) -> "PgSTAC":
        # If DSN set in the environment, use that.
        dsn = os.environ.get("POSTGRES_DSN")
        if dsn:
            return PgSTAC(dsn)

        user = os.environ.get("POSTGRES_USER")
        if user is None:
            raise ValueError("POSTGRES_USER is not set!")
        password = os.environ.get("POSTGRES_PASS")
        if password is None:
            raise ValueError("POSTGRES_PASS is not set!")
        host = os.environ.get("POSTGRES_HOST")
        if host is None:
            raise ValueError("POSTGRES_HOST is not set!")
        port = os.environ.get("POSTGRES_PORT")
        if port is None:
            raise ValueError("POSTGRES_PORT is not set!")
        dbname = os.environ.get("POSTGRES_DBNAME")
        if dbname is None:
            raise ValueError("POSTGRES_DBNAME is not set!")
        pg_connenction_str = f"postgresql://{user}:{password}@{host}:{port}/{dbname}"
        return PgSTAC(pg_connenction_str)
