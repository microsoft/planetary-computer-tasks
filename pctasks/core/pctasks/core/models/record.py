from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, Optional

from pctasks.core.constants import RECORD_SCHEMA_VERSION
from pctasks.core.models.base import PCBaseModel

TYPE_FIELD_NAME = "type"


class Record(PCBaseModel, ABC):
    type: str
    schema_version: str = RECORD_SCHEMA_VERSION

    # These fields are updated by the comsodb
    # BaseCosmosDBContainer logic during puts.
    created: Optional[datetime] = None
    updated: Optional[datetime] = None

    deleted: bool = False
    """Whether this record is deleted or not.

    This is a soft delete that appears in the cosmosdb change feed.
    """

    @abstractmethod
    def get_id(self) -> str:
        ...

    @staticmethod
    def migrate(item: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate a record to the latest schema version.

        Records should override this method to migrate to the latest schema version.
        """
        return item
