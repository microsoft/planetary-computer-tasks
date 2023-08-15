from typing import Dict, Optional, Type, TypeVar

from pydantic import BaseModel

from pctasks.core.cosmos.container import (
    ContainerOperation,
    CosmosDBContainer,
    CosmosDBDatabase,
    TriggerType,
)
from pctasks.core.cosmos.settings import CosmosDBSettings
from pctasks.core.models.event import CreateItemErrorRecord, IngestItemErrorRecord

# Records that this container can hold
T = TypeVar(
    "T",
    CreateItemErrorRecord,
    IngestItemErrorRecord,
)


PARTITION_KEY = "/id"

STORED_PROCEDURES: Dict[ContainerOperation, Dict[Type[BaseModel], str]] = {}

TRIGGERS: Dict[ContainerOperation, Dict[TriggerType, str]] = {}


class ProcessItemErrorsContainer(CosmosDBContainer[T]):
    """
    CosmosDB Container for error records from item creation or ingest.
    """

    def __init__(
        self,
        model_type: Type[T],
        db: Optional[CosmosDBDatabase] = None,
        settings: Optional[CosmosDBSettings] = None,
    ) -> None:
        super().__init__(
            lambda settings: settings.get_process_item_errors_container_name(),
            PARTITION_KEY,
            model_type=model_type,  # type: ignore[arg-type]
            db=db,
            settings=settings,
            stored_procedures=STORED_PROCEDURES,
            triggers=TRIGGERS,
        )

    def get_partition_key(self, model: T) -> str:
        return model.id
