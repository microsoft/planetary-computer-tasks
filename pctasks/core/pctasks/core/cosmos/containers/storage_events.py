from typing import Dict, Optional, Type

from pydantic import BaseModel

from pctasks.core._compat import TypeAlias
from pctasks.core.cosmos.container import (
    ContainerOperation,
    CosmosDBContainer,
    CosmosDBDatabase,
    TriggerType,
)
from pctasks.core.cosmos.settings import CosmosDBSettings
from pctasks.core.models.event import StorageEventRecord

T: TypeAlias = StorageEventRecord

PARTITION_KEY = "/id"

STORED_PROCEDURES: Dict[ContainerOperation, Dict[Type[BaseModel], str]] = {}

TRIGGERS: Dict[ContainerOperation, Dict[TriggerType, str]] = {}


class StorageEventsContainer(CosmosDBContainer[T]):
    def __init__(
        self,
        model_type: Type[T],
        db: Optional[CosmosDBDatabase] = None,
        settings: Optional[CosmosDBSettings] = None,
    ) -> None:
        super().__init__(
            lambda settings: settings.get_storage_events_container_name(),
            PARTITION_KEY,
            model_type=model_type,
            db=db,
            settings=settings,
            stored_procedures=STORED_PROCEDURES,
            triggers=TRIGGERS,
        )

    def get_partition_key(self, model: T) -> str:
        return model.id
