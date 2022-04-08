import json
import logging
import os
from tempfile import TemporaryDirectory
from typing import Any, Dict, Iterable, Optional, Set

from pypgstac.db import PgstacDB
from pypgstac.load import Loader, Methods

from pctasks.core.utils import grouped

logger = logging.getLogger(__name__)


class PgSTAC:
    def __init__(self, pg_connection_string: str) -> None:
        self.db = PgstacDB(pg_connection_string, debug=True)
        # self.db.connect()
        self.loader = Loader(self.db)

    def ingest_items(
        self,
        items: Iterable[bytes],
        mode: Methods = Methods.upsert,
        insert_group_size: Optional[int] = None,
    ) -> None:
        if insert_group_size:
            groups = grouped(items, insert_group_size)
        else:
            groups = [items]

        with TemporaryDirectory() as tmpdir:
            for i, group in enumerate(groups):
                fname = f"{i}.ndjson"
                path = os.path.join(tmpdir, fname)
                logger.info(f"  ...Loading group {i+1}")
                with open(path, "wb") as f:
                    f.write(b"\n".join([x.strip() for x in group]))

                self.loader.load_items(path, insert_mode=mode)

    def ingest_collections(
        self,
        collections: Iterable[Dict[str, Any]],
        mode: Methods = Methods.upsert,
    ) -> None:
        # TODO: Remove when we don't have to use files.
        with TemporaryDirectory() as tmpdir:
            path = "collections.ndjson"
            with open(os.path.join(tmpdir, path), "wb") as f:
                f.write(
                    b"\n".join([json.dumps(c).encode("utf-8") for c in collections])
                )
            self.loader.load_collections(
                os.path.join(tmpdir, path), insert_mode=mode
            )

    def existing_items(self, collection_id: str, item_ids: Set[str]) -> Set[str]:
        """The IDs of Items that already exist in the database."""
        rows = self.db.query(
            """
                SELECT id from items where id = ANY(%s) and collection = %s
            """,
            args=[list(item_ids), collection_id],
        )
        return set([row[0] for row in rows])

    def collection_exists(self, collection_id: str) -> bool:
        rows = self.db.query(
            """
                SELECT id from collections where id = %s
            """,
            args=[collection_id],
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
