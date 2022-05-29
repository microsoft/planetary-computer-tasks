import logging
from typing import Any, Dict, List

# from pypgstac.pypgstac import loadopt
from pypgstac.load import Methods

from pctasks.ingest_task.pgstac import PgSTAC

logger = logging.getLogger(__name__)


def ingest_collection(
    pgstac: PgSTAC,
    collection: Dict[str, Any],
) -> bool:
    """Ingests a collection.

    Returns True if the collection was inserted, False if it was updated.
    """
    import json

    logger.info(json.dumps(collection, indent=2))
    collection_id = collection["id"]
    logger.info(f"Ingesting collection {collection_id}")
    insert = not pgstac.collection_exists(collection_id)
    pgstac.ingest_collections(
        [collection], mode=Methods.insert if insert else Methods.upsert
    )
    return insert


def ingest_collections(
    pgstac: PgSTAC,
    collections: List[Dict[str, Any]],
) -> Dict[str, bool]:
    """Ingests collections.

    Returns a dict of collection_id -> True if was inserted, False if was updated.
    """
    return {
        collection["id"]: ingest_collection(pgstac, collection)
        for collection in collections
    }
