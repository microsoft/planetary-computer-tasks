from typing import Any, Dict, List, Optional, Union

from pydantic import Field, validator

from pctasks.core.models.base import PCBaseModel
from pctasks.core.models.event import STACCollectionEventType, STACItemEventType
from pctasks.core.models.task import TaskDefinition
from pctasks.ingest.constants import (
    COLLECTION_TASK_ID,
    COLLECTIONS_MESSAGE_TYPE,
    DB_CONNECTION_STRING_ENV_VAR,
    INGEST_TASK,
    ITEM_TASK_ID,
    NDJSON_MESSAGE_TYPE,
    NDJSON_TASK_ID,
)
from pctasks.ingest.settings import IngestOptions, IngestSettings


class InvalidSTACException(Exception):
    pass


class NdjsonFolder(PCBaseModel):
    uri: str
    name_starts_with: Optional[str] = None
    extensions: Optional[List[str]] = None
    ends_with: Optional[str] = None
    matches: Optional[str] = None
    limit: Optional[int] = None


class IngestNdjsonInput(PCBaseModel):
    type: str = Field(default=NDJSON_MESSAGE_TYPE, const=True)
    uris: Optional[Union[str, List[str]]] = None
    ndjson_folder: Optional[NdjsonFolder] = None

    @validator("ndjson_folder")
    def _validate_ndjson_folder(
        cls, v: Optional[NdjsonFolder], values: Dict[str, Any]
    ) -> Optional[NdjsonFolder]:
        if v is None:
            if values["uris"] is None:
                raise ValueError("Either ndjson_folder or uris must be provided.")
        return v


class IngestCollectionsInput(PCBaseModel):
    type: str = Field(default=COLLECTIONS_MESSAGE_TYPE, const=True)
    collections: List[Dict[str, Any]]


class IngestTaskInput(PCBaseModel):
    content: Union[IngestNdjsonInput, IngestCollectionsInput, Dict[str, Any]]
    """The content of the message.

    Can be a STAC Collection or Item JSON dict, or a NdjsonMessageData object.
    """

    options: IngestOptions = Field(default_factory=IngestOptions)


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


class IngestTaskConfig(TaskDefinition):
    @classmethod
    def create(
        cls,
        task_id: str,
        content: Union[IngestNdjsonInput, IngestCollectionsInput, Dict[str, Any]],
        image_key: Optional[str] = None,
        target: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
        environment: Optional[Dict[str, str]] = None,
        options: Optional[IngestOptions] = None,
        ingest_settings: Optional[IngestSettings] = None,
        add_service_principal: bool = False,
    ) -> TaskDefinition:
        data = IngestTaskInput(
            content=content,
            options=options or IngestOptions(),
        )

        settings = ingest_settings or IngestSettings.get()

        if not image_key:
            image_key = settings.image_keys.get_key(target)

        if not image_key and (
            not environment or DB_CONNECTION_STRING_ENV_VAR not in environment
        ):
            raise ValueError(
                "Must supply image_key or "
                f"environment[{DB_CONNECTION_STRING_ENV_VAR}]"
            )

        environment = environment or {}
        if add_service_principal:
            environment.setdefault("AZURE_TENANT_ID", "${{ secrets.task-tenant-id }}")
            environment.setdefault("AZURE_CLIENT_ID", "${{ secrets.task-client-id }}")
            environment.setdefault(
                "AZURE_CLIENT_SECRET", "${{ secrets.task-client-secret }}"
            )

        return TaskDefinition(
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
        options: Optional[IngestOptions] = None,
        ingest_settings: Optional[IngestSettings] = None,
        add_service_principal: bool = False,
    ) -> TaskDefinition:
        if "collection" not in item:
            raise InvalidSTACException("Item is missing a collection.")

        return cls.create(
            task_id=ITEM_TASK_ID,
            content=item,
            target=target,
            tags=tags,
            environment=environment,
            options=options,
            ingest_settings=ingest_settings,
            add_service_principal=add_service_principal,
        )

    @classmethod
    def from_collection(
        cls,
        collection: Dict[str, Any],
        target: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
        environment: Optional[Dict[str, str]] = None,
        options: Optional[IngestOptions] = None,
        ingest_settings: Optional[IngestSettings] = None,
        add_service_principal: bool = False,
    ) -> TaskDefinition:
        if "id" not in collection:
            raise InvalidSTACException("Collection is missing an id.")

        return cls.create(
            task_id=COLLECTION_TASK_ID,
            content=collection,
            target=target,
            tags=tags,
            environment=environment,
            options=options,
            ingest_settings=ingest_settings,
            add_service_principal=add_service_principal,
        )

    @classmethod
    def from_collections(
        cls,
        collections: List[Dict[str, Any]],
        target: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
        environment: Optional[Dict[str, str]] = None,
        options: Optional[IngestOptions] = None,
        ingest_settings: Optional[IngestSettings] = None,
        add_service_principal: bool = False,
    ) -> TaskDefinition:

        return cls.create(
            task_id=COLLECTION_TASK_ID,
            content=IngestCollectionsInput(collections=collections),
            target=target,
            tags=tags,
            environment=environment,
            options=options,
            ingest_settings=ingest_settings,
            add_service_principal=add_service_principal,
        )

    @classmethod
    def from_ndjson(
        cls,
        ndjson_data: IngestNdjsonInput,
        target: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
        environment: Optional[Dict[str, str]] = None,
        option: Optional[IngestOptions] = None,
        ingest_settings: Optional[IngestSettings] = None,
        add_service_principal: bool = False,
    ) -> TaskDefinition:
        return cls.create(
            task_id=NDJSON_TASK_ID,
            content=ndjson_data,
            target=target,
            tags=tags,
            environment=environment,
            options=option,
            ingest_settings=ingest_settings,
            add_service_principal=add_service_principal,
        )
