import logging
import os
from typing import List, Optional, Union

from pctasks.core.models.event import STACCollectionEventType, STACItemEventType
from pctasks.core.models.task import FailedTaskResult, WaitTaskResult
from pctasks.ingest.constants import COLLECTIONS_MESSAGE_TYPE, NDJSON_MESSAGE_TYPE
from pctasks.ingest.models import (
    CollectionIngestTaskOutput,
    IngestCollectionsInput,
    IngestNdjsonInput,
    IngestTaskInput,
    IngestTaskOutput,
    ItemIngestTaskOutput,
)
from pctasks.ingest_task.collection import ingest_collection, ingest_collections
from pctasks.ingest_task.constants import DB_CONNECTION_STRING_ENV_VALUE
from pctasks.ingest_task.items import ingest_item, ingest_ndjsons
from pctasks.ingest_task.pgstac import PgSTAC
from pctasks.task.context import TaskContext
from pctasks.task.task import Task

logger = logging.getLogger(__name__)


def get_url(
    stac_api_url: str, owner: str, collection_id: str, item_id: Optional[str] = None
) -> str:
    """Gets the subject URL"""
    url = os.path.join(stac_api_url, "collections", collection_id)
    if item_id:
        url = os.path.join(url, "items", item_id)
    return url


class IngestError(Exception):
    pass


class IngestTask(Task[IngestTaskInput, IngestTaskOutput]):
    _input_model = IngestTaskInput
    _output_model = IngestTaskOutput

    def get_required_environment_variables(self) -> List[str]:
        return [DB_CONNECTION_STRING_ENV_VALUE]

    def run(
        self, input: IngestTaskInput, context: TaskContext
    ) -> Union[IngestTaskOutput, WaitTaskResult, FailedTaskResult]:
        content = input.content

        conn_str = os.environ[DB_CONNECTION_STRING_ENV_VALUE]

        pgstac = PgSTAC(conn_str)

        with pgstac.db:

            item_id: Optional[str] = None

            if isinstance(content, IngestNdjsonInput):
                ndjson_uris: List[str]
                uris = content.uris
                if uris:
                    if isinstance(uris, str):
                        ndjson_uris = [uris]
                    else:
                        ndjson_uris = uris
                else:
                    folder_config = content.ndjson_folder
                    if not folder_config:
                        # Should be caught by the validator
                        raise IngestError(
                            "Either ndjson_folder or uris must be provided."
                        )
                    ndjson_storage = context.storage_factory.get_storage(
                        folder_config.uri
                    )
                    ndjson_uris = [
                        ndjson_storage.get_uri(path)
                        for path in ndjson_storage.list_files(
                            name_starts_with=folder_config.name_starts_with,
                            extensions=folder_config.extensions,
                            ends_with=folder_config.ends_with,
                            matches=folder_config.matches,
                        )
                    ]
                    if folder_config.limit:
                        ndjson_uris = ndjson_uris[: folder_config.limit]

                ingest_ndjsons(
                    pgstac, ndjson_uris, storage_factory=context.storage_factory
                )
                result = IngestTaskOutput(bulk_load=True)

            elif isinstance(content, IngestCollectionsInput):
                collections_to_status = ingest_collections(pgstac, content.collections)
                result = IngestTaskOutput(
                    collections=[
                        CollectionIngestTaskOutput(
                            collection_id=collection_id,
                            event_type=STACCollectionEventType.CREATED
                            if inserted
                            else STACCollectionEventType.UPDATED,
                        )
                        for collection_id, inserted in collections_to_status.items()
                    ]
                )
            else:
                assert isinstance(content, dict)
                ingest_type = content.get("type")
                if not ingest_type:
                    raise Exception("Ingest task data must contain a type")

                if ingest_type == "Collection":
                    collection_id = content.get("id")
                    if not collection_id:
                        raise IngestError("Collection must contain an id")
                    inserted = ingest_collection(pgstac, content)

                    result = IngestTaskOutput(
                        collections=[
                            CollectionIngestTaskOutput(
                                collection_id=collection_id,
                                event_type=STACCollectionEventType.CREATED
                                if inserted
                                else STACCollectionEventType.UPDATED,
                            )
                        ]
                    )

                elif ingest_type == "Feature":
                    item_id = content.get("id")
                    if not item_id:
                        raise IngestError("Item must contain an id")
                    geometry = content.get("geometry")
                    if not geometry:
                        raise IngestError("Item must contain a geometry")
                    collection_id = content.get("collection")
                    if not collection_id:
                        raise IngestError("Item must contain a collection")

                    inserted = item_id not in pgstac.existing_items(
                        collection_id, {item_id or ""}
                    )

                    # Ingest item
                    ingest_item(pgstac, content)

                    result = IngestTaskOutput(
                        items=[
                            ItemIngestTaskOutput(
                                collection_id=collection_id,
                                item_id=item_id,
                                geometry=geometry,
                                event_type=STACItemEventType.CREATED
                                if not inserted
                                else STACItemEventType.UPDATED,
                            )
                        ]
                    )
                else:
                    # Check for message validation errors that
                    # caused fallback to Dict[str, Any]
                    if ingest_type == COLLECTIONS_MESSAGE_TYPE:
                        IngestCollectionsInput(**content)
                    if ingest_type == NDJSON_MESSAGE_TYPE:
                        IngestNdjsonInput(**content)

                    raise ValueError(f"Unknown type {ingest_type}")

            return result


ingest_task = IngestTask()
