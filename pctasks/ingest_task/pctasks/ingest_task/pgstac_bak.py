# import asyncio
# import logging
# import os
# from typing import Iterable, Optional, Set

# from pypgstac.load import T  # TypeVar for ingestable Iterables
# from pypgstac.load import DB, load_iterator, loadopt, tables

# from pctasks.core.utils import grouped

# logger = logging.getLogger(__name__)


# class PgSTAC(DB):
#     def __init__(self, pg_connection_string: str = None):
#         self.pg_connection_string = pg_connection_string

#     async def ingest_items_async(
#         self,
#         items: Iterable[bytes],
#         mode: loadopt = loadopt("upsert"),
#         insert_group_size: Optional[int] = None,
#     ) -> None:
#         if insert_group_size:
#             groups = grouped(items, insert_group_size)
#         else:
#             groups = [items]
#         conn = await self.create_connection()
#         try:
#             for i, group in enumerate(groups):
#                 logger.info(f"  ...Loading group {i+1}")
#                 async with conn.transaction():
#                     await load_iterator(group, tables("items"), conn, mode)
#         finally:
#             await conn.close()

#     def ingest_items(
#         self,
#         items: Iterable[bytes],
#         mode: loadopt = loadopt("upsert"),
#         insert_group_size: Optional[int] = None,
#     ) -> None:
#         asyncio.run(self.ingest_items_async(items, mode, insert_group_size))

#     async def ingest_collections_async(
#         self,
#         collections: T,
#         mode: loadopt = loadopt("upsert"),
#     ) -> None:
#         conn = await self.create_connection()
#         try:
#             async with conn.transaction():
#                 logger.debug(f"collections: {collections}")
#                 await load_iterator(collections, tables("collections"), conn, mode)
#         finally:
#             await conn.close()

#     def ingest_collections(
#         self,
#         collections: T,
#         mode: loadopt = loadopt("upsert"),
#     ) -> None:
#         asyncio.run(self.ingest_collections_async(collections, mode))

#     async def existing_items_async(self, item_ids: Set[str]) -> Set[str]:
#         """The IDs of Items that already exist in the database."""
#         conn = await self.create_connection()
#         try:
#             async with conn.transaction():
#                 rows = await conn.fetch(
#                     """
#                    SELECT id from items where id = ANY($1::text[])
#                 """,
#                     item_ids,
#                 )

#                 return set([row["id"] for row in rows])

#         finally:
#             await conn.close()

#     def existing_items(self, item_ids: Set[str]) -> Set[str]:
#         """The IDs of Items that already exist in the database."""
#         return asyncio.run(self.existing_items_async(item_ids))

#     async def collection_exists_async(self, collection_id: str) -> bool:
#         conn = await self.create_connection()
#         try:
#             async with conn.transaction():
#                 rows = await conn.fetch(
#                     """
#                    SELECT id from collections where id = $1
#                 """,
#                     collection_id,
#                 )

#                 return any(rows)

#         finally:
#             await conn.close()

#     def collection_exists(self, collection_id: str) -> bool:
#         return asyncio.run(self.collection_exists_async(collection_id))

#     @classmethod
#     def from_env(cls) -> "PgSTAC":
#         # If DSN set in the environment, use that.
#         dsn = os.environ.get("POSTGRES_DSN")
#         if dsn:
#             return PgSTAC(dsn)

#         user = os.environ.get("POSTGRES_USER")
#         if user is None:
#             raise ValueError("POSTGRES_USER is not set!")
#         password = os.environ.get("POSTGRES_PASS")
#         if password is None:
#             raise ValueError("POSTGRES_PASS is not set!")
#         host = os.environ.get("POSTGRES_HOST")
#         if host is None:
#             raise ValueError("POSTGRES_HOST is not set!")
#         port = os.environ.get("POSTGRES_PORT")
#         if port is None:
#             raise ValueError("POSTGRES_PORT is not set!")
#         dbname = os.environ.get("POSTGRES_DBNAME")
#         if dbname is None:
#             raise ValueError("POSTGRES_DBNAME is not set!")
#         pg_connenction_str = f"postgresql://{user}:{password}@{host}:{port}/{dbname}"
#         return PgSTAC(pg_connenction_str)
