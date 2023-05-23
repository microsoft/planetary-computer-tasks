from typing import Any, Dict, Optional, Union
from uuid import uuid4

from pydantic import BaseModel, Field

from pctasks.core.constants import MICROSOFT_OWNER
from pctasks.core.models.base import ForeachConfig, PCBaseModel, RunRecordId
from pctasks.core.models.record import Record
from pctasks.core.models.utils import tzutc_now
from pctasks.core.utils import StrEnum


class CloudEvent(PCBaseModel):
    spec_version: str = Field(default="1.0", const=True, alias="specversion")
    type: str
    source: str
    subject: Optional[str] = None
    id: str = Field(default_factory=lambda: uuid4().hex)
    time: str = Field(default_factory=lambda: tzutc_now().isoformat())
    data_content_type: str = Field(default="application/json", alias="datacontenttype")
    data: Union[Dict[str, Any], BaseModel]


class StorageEventType(StrEnum):
    # Doesn't have an update
    CREATED = "Microsoft.Storage.BlobCreated"
    DELETED = "Microsoft.Storage.BlobDeleted"


class StorageEventData(PCBaseModel):
    """
    A model for Blob Storage Events.

    https://learn.microsoft.com/en-us/azure/event-grid/event-schema-blob-storage?tabs=cloud-event-schema
    """

    api: str
    clientRequestId: str
    requestId: str
    eTag: str
    contentType: str
    contentLength: Optional[int]
    contentOffset: Optional[int]
    blobType: str
    url: str
    sequencer: str
    storageDiagnostics: Dict[str, str]


class StorageEvent(CloudEvent):
    type: StorageEventType
    data: StorageEventData


class StorageEventRecord(StorageEvent, Record):
    """
    A Cosmos DB record for storage events.

    Cloud Events are valid Cosmos DB records, so we just inherit the
    additional methods from Record to satisfy mypy.
    """

    # We need to repeat this type definition to please mypy, which
    # didn't like the "conflicting" definitions for 'type', despite
    # them both being strings at the end of the day.
    type: StorageEventType

    def get_id(self) -> str:
        return self.id

    @staticmethod
    def migrate(item: Dict[str, Any]) -> Dict[str, Any]:
        return item


class CreateItemError(Record):
    """
    Error record for when an item creation fails.
    """

    id: str = Field(default_factory=lambda: uuid4().hex)
    input: StorageEvent
    traceback: str
    attempt: int
    run_id: str

    def get_id(self) -> str:
        return self.id


class STACItemEventType(StrEnum):
    CREATED = "Microsoft.PlanetaryComputer.ItemCreated"
    UPDATED = "Microsoft.PlanetaryComputer.ItemUpdated"
    DELETED = "Microsoft.PlanetaryComputer.ItemDeleted"


class STACItemEventData(PCBaseModel):
    owner: str
    collection_id: str
    item_id: str
    geometry: Optional[Dict[str, Any]]


class STACItemEvent(CloudEvent):
    type: STACItemEventType
    data: STACItemEventData

    @classmethod
    def create(
        cls,
        collection_id: str,
        item_id: str,
        event_type: STACItemEventType,
        data: STACItemEventData,
    ) -> "STACItemEvent":
        return cls(
            type=event_type,
            source=f"/{data.owner}/collections/{collection_id}",
            subject=f"/items/{item_id}",
            data=data,
        )


class STACCollectionEventType(StrEnum):
    CREATED = "Microsoft.PlanetaryComputer.CollectionCreated"
    UPDATED = "Microsoft.PlanetaryComputer.CollectionUpdated"
    DELETED = "Microsoft.PlanetaryComputer.CollectionDeleted"


class STACCollectionEventData(PCBaseModel):
    owner: str
    collection_id: str


class STACCollectionEvent(CloudEvent):
    type: STACCollectionEventType
    data: STACCollectionEventData

    @classmethod
    def create(
        cls,
        collection_id: str,
        event_type: STACCollectionEventType,
        data: STACCollectionEventData,
    ) -> "STACCollectionEvent":
        return cls(
            type=event_type,
            source=f"/{data.owner}",
            subject=f"/collections/{collection_id}",
            data=data,
        )


class NotificationMessage(PCBaseModel):
    event: CloudEvent


class NotificationSubmitMessage(PCBaseModel):
    notification: NotificationMessage
    target_environment: Optional[str]
    type: str = Field(default="Notification", const=True)
    processing_id: RunRecordId


class NotificationConfig(PCBaseModel):
    type: str
    foreach: Optional[ForeachConfig] = None


class ItemNotificationConfig(NotificationConfig):
    type: str = Field(default="Item", const=True)
    owner: str = MICROSOFT_OWNER
    collection_id: str
    item_id: str
    geometry: Dict[str, Any]
    event_type: STACItemEventType

    def to_message(self) -> NotificationMessage:
        return NotificationMessage(
            event=STACItemEvent.create(
                event_type=self.event_type,
                collection_id=self.collection_id,
                item_id=self.item_id,
                data=STACItemEventData(
                    owner=self.owner,
                    collection_id=self.collection_id,
                    item_id=self.item_id,
                    geometry=self.geometry,
                ),
            )
        )
