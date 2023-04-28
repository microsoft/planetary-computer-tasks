from datetime import datetime
from typing import Any, Dict, Optional

import pystac
from pydantic import Field, validator

from pctasks.core.models.record import Record
from pctasks.core.utils import StrEnum


class ItemRecordType(StrEnum):
    STAC_ITEM = "StacItem"
    ITEM_UPDATED = "ItemUpdated"


class ItemRecord(Record):
    type: ItemRecordType
    stac_id: str

    @validator("stac_id")
    def _stac_id_validator(cls, v: str) -> str:
        # Ensure a single forward slash in the string
        if v.count("/") != 1:
            raise ValueError("stac_id must contain a single forward slash")
        return v

    def get_id(self) -> str:
        version = getattr(self, "version", "")
        return f"{self.collection_id}:{self.item_id}:{version}:{self.type}"

    @property
    def collection_id(self) -> str:
        return self.stac_id.split("/")[0]

    @property
    def item_id(self) -> str:
        return self.stac_id.split("/")[1]


class StacItemRecord(ItemRecord):
    """
    Record for STAC items.

    These records are used in the items container of the Cosmos DB database.

    Parameters
    ----------
    type: ItemRecordType, 'StacItem'
        This is always 'StacItem'
    stac_id: str
        The "STAC identifier" which is the STAC collection ID and Item ID joined
        by a single ``/``
    version: str, optional
        The STAC version identifier.
    """

    type: ItemRecordType = Field(default=ItemRecordType.STAC_ITEM, const=True)
    item: Dict[str, Any]
    deleted: bool = False

    @classmethod
    def from_item(cls, item: pystac.Item) -> "StacItemRecord":
        collection_id = item.collection_id
        item_id = item.id
        stac_id = f"{collection_id}/{item_id}"
        return cls(
            stac_id=stac_id, version=item.properties.get("version"), item=item.to_dict()
        )

    @property
    def version(self) -> str:
        return self.item.get("properties", {}).get("version", "")


class ItemUpdatedRecord(ItemRecord):
    """Record that records an item update.

    Does not specify if the item was created or updated.
    """

    type: ItemRecordType = Field(default=ItemRecordType.ITEM_UPDATED, const=True)

    run_id: str
    """The run ID of the workflow that updated this Item version"""

    delete: bool = False
    """True if the update was to delete this Item version"""

    storage_event_time: Optional[datetime] = None
    message_inserted_time: Optional[datetime] = None
    version: Optional[str]

    @validator("version")
    def _version_validator(cls, v: Optional[str]) -> str:
        return v or ""
