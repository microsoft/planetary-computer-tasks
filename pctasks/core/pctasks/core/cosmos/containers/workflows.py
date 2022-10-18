from typing import Dict, Optional, Type, TypeVar

from pydantic import BaseModel

from pctasks.core.cosmos.container import (
    ContainerOperation,
    CosmosDBContainer,
    CosmosDBDatabase,
    TriggerType,
)
from pctasks.core.cosmos.settings import CosmosDBSettings
from pctasks.core.models.run import WorkflowRunRecord
from pctasks.core.models.workflow import WorkflowRecord

# Records that this container can hold
T = TypeVar("T", WorkflowRecord, WorkflowRunRecord)

PARTITION_KEY = "/workflow_id"

STORED_PROCEDURES: Dict[ContainerOperation, Dict[Type[BaseModel], str]] = {}

TRIGGERS: Dict[ContainerOperation, Dict[TriggerType, str]] = {
    ContainerOperation.PUT: {TriggerType.POST: "post-all-workflows"}
}


class WorkflowsContainer(CosmosDBContainer[T]):
    def __init__(
        self,
        model_type: Type[T],
        db: Optional[CosmosDBDatabase] = None,
        settings: Optional[CosmosDBSettings] = None,
    ) -> None:
        if not settings:
            settings = CosmosDBSettings.get()
        if not db:
            db = CosmosDBDatabase(settings)
        super().__init__(
            settings.workflows_container_name,
            PARTITION_KEY,
            model_type=model_type,  # type: ignore[arg-type]
            db=db,
            stored_procedures=STORED_PROCEDURES,
            triggers=TRIGGERS,
        )

    def get_partition_key(self, model: T) -> str:
        return model.workflow_id
