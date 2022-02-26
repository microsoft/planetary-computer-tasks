from typing import Any, Dict, List, Optional, Union

from pydantic import Field, validator

from pctasks.core.models.base import PCBaseModel
from pctasks.core.models.event import STACCollectionEventType, STACItemEventType
from pctasks.core.models.task import TaskConfig
from pctasks.ingest.constants import (
    COLLECTION_TASK_ID,
    COLLECTIONS_MESSAGE_TYPE,
    INGEST_TASK,
    ITEM_TASK_ID,
    NDJSON_MESSAGE_TYPE,
    NDJSON_TASK_ID,
)
from pctasks.ingest.settings import IngestConfig, IngestSettings


class InvalidSTACException(Exception):
    pass


class IngestNdjsonInput(PCBaseModel):
    type: str = Field(default=NDJSON_MESSAGE_TYPE, const=True)
    collection: str
    uris: List[str]


class IngestCollectionsInput(PCBaseModel):
    type: str = Field(default=COLLECTIONS_MESSAGE_TYPE, const=True)
    collections: List[Dict[str, Any]]


class IngestTaskInput(PCBaseModel):
    content: Union[IngestNdjsonInput, IngestCollectionsInput, Dict[str, Any]]
    """The content of the message.

    Can be a STAC Collection or Item JSON dict, or a NdjsonMessageData object.
    """

    config: IngestConfig = Field(default_factory=IngestConfig)


class CollectionIngestTaskOutput(PCBaseModel):
    collection_id: str
    event_type: STACCollectionEventType


class ItemIngestTaskOutput(PCBaseModel):
    collection_id: str
    item_id: str
    geometry: Dict[str, Any]
    event_type: STACItemEventType


class IngestTaskOutput(PCBaseModel):
    bulk_load: bool = False
    """Whether to bulk load the item data into the database."""
    collections: Optional[List[CollectionIngestTaskOutput]] = None
    """List of collections created by the ingest task."""
    items: Optional[List[ItemIngestTaskOutput]] = None
    """List of items created by the ingest task."""

    @validator("items", always=True)
    def _validate_items(cls, v: Any, values: Dict[str, Any]) -> Any:
        if not v and values["collections"] is None and not values["bulk_load"]:
            raise ValueError("Must supply either collections or items")
        return v


class IngestTaskConfig(TaskConfig):
    @classmethod
    def create(
        cls,
        task_id: str,
        content: Union[IngestNdjsonInput, IngestCollectionsInput, Dict[str, Any]],
        target: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
        environment: Optional[Dict[str, str]] = None,
        ingest_config: Optional[IngestConfig] = None,
        ingest_settings: Optional[IngestSettings] = None,
    ) -> TaskConfig:
        data = IngestTaskInput(
            content=content,
            config=ingest_config or IngestConfig(),
        )

        settings = ingest_settings or IngestSettings.get()

        image_key = settings.image_keys.get_key(target)

        return TaskConfig(
            id=task_id,
            image=None,
            image_key=image_key,
            task=INGEST_TASK,
            tags=tags,
            environment=environment,
            args=data.dict(),
        )

    @classmethod
    def from_item(
        cls,
        item: Dict[str, Any],
        target: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
        environment: Optional[Dict[str, str]] = None,
        ingest_config: Optional[IngestConfig] = None,
        ingest_settings: Optional[IngestSettings] = None,
    ) -> TaskConfig:
        if "collection" not in item:
            raise InvalidSTACException("Item is missing a collection.")

        return cls.create(
            task_id=ITEM_TASK_ID,
            content=item,
            target=target,
            tags=tags,
            environment=environment,
            ingest_config=ingest_config,
            ingest_settings=ingest_settings,
        )

    @classmethod
    def from_collection(
        cls,
        collection: Dict[str, Any],
        target: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
        environment: Optional[Dict[str, str]] = None,
        ingest_config: Optional[IngestConfig] = None,
        ingest_settings: Optional[IngestSettings] = None,
    ) -> TaskConfig:
        if "id" not in collection:
            raise InvalidSTACException("Collection is missing an id.")

        return cls.create(
            task_id=COLLECTION_TASK_ID,
            content=collection,
            target=target,
            tags=tags,
            environment=environment,
            ingest_config=ingest_config,
            ingest_settings=ingest_settings,
        )

    @classmethod
    def from_collections(
        cls,
        collections: List[Dict[str, Any]],
        target: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
        environment: Optional[Dict[str, str]] = None,
        ingest_config: Optional[IngestConfig] = None,
        ingest_settings: Optional[IngestSettings] = None,
    ) -> TaskConfig:

        return cls.create(
            task_id=COLLECTION_TASK_ID,
            content=IngestCollectionsInput(collections=collections),
            target=target,
            tags=tags,
            environment=environment,
            ingest_config=ingest_config,
            ingest_settings=ingest_settings,
        )

    @classmethod
    def from_ndjson(
        cls,
        ndjson_data: IngestNdjsonInput,
        target: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
        environment: Optional[Dict[str, str]] = None,
        ingest_config: Optional[IngestConfig] = None,
        ingest_settings: Optional[IngestSettings] = None,
    ) -> TaskConfig:
        return cls.create(
            task_id=NDJSON_TASK_ID,
            content=ndjson_data,
            target=target,
            tags=tags,
            environment=environment,
            ingest_config=ingest_config,
            ingest_settings=ingest_settings,
        )
