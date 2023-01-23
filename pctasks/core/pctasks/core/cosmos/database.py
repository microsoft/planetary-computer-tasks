from dataclasses import dataclass
from typing import Optional

from azure.cosmos import ContainerProxy, CosmosClient, DatabaseProxy
from azure.cosmos.aio import ContainerProxy as AsyncContainerProxy
from azure.cosmos.aio import CosmosClient as AsyncCosmosClient
from azure.cosmos.aio import DatabaseProxy as AsyncDatabaseProxy

from pctasks.core.cosmos.settings import CosmosDBSettings


@dataclass
class CosmosDBClients:
    service: CosmosClient
    database: DatabaseProxy
    container: ContainerProxy

    def close(self) -> None:
        self.service.__exit__()


@dataclass
class AsyncCosmosDBClients:
    service: AsyncCosmosClient
    database: AsyncDatabaseProxy
    container: AsyncContainerProxy

    async def close(self) -> None:
        await self.service.__aexit__()


class CosmosDBDatabase:
    settings: CosmosDBSettings
    client: CosmosClient
    db: DatabaseProxy

    def __init__(self, settings: Optional[CosmosDBSettings] = None) -> None:
        if not settings:
            settings = CosmosDBSettings.get()
        self.settings = settings

    def create_clients(self, container_name: str) -> CosmosDBClients:
        client = self.settings.get_client()
        db = client.get_database_client(self.settings.database)
        container = db.get_container_client(container_name)
        return CosmosDBClients(client, db, container)

    def create_async_clients(self, container_name: str) -> AsyncCosmosDBClients:
        client = self.settings.get_async_client()
        db = client.get_database_client(self.settings.database)
        container = db.get_container_client(container_name)
        return AsyncCosmosDBClients(client, db, container)
