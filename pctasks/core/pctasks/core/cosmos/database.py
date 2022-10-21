from typing import Dict, Optional, TypeVar

from azure.cosmos import ContainerProxy, CosmosClient, DatabaseProxy
from pydantic import BaseModel

from pctasks.core.cosmos.settings import CosmosDBSettings

T = TypeVar("T", bound=BaseModel)


class CosmosDBDatabase:
    settings: CosmosDBSettings
    client: CosmosClient
    db: DatabaseProxy
    _container_clients: Dict[str, ContainerProxy]

    def __init__(self, settings: Optional[CosmosDBSettings] = None) -> None:
        if not settings:
            settings = CosmosDBSettings.get()
        self.settings = settings
        self.client = self.settings.get_client()
        self.db = self.client.get_database_client(settings.database)
        self._container_clients: Dict[str, ContainerProxy] = {}

    def get_container_client(self, name: str) -> ContainerProxy:
        if name not in self._container_clients:
            self._container_clients[name] = self.db.get_container_client(name)
        return self._container_clients[name]
