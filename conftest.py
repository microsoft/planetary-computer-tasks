from typing import Iterator

import pytest

from pctasks.dev.cosmosdb import temp_cosmosdb_if_emulator
from pctasks.core.cosmos.database import CosmosDBDatabase, CosmosDBSettings


@pytest.fixture(scope="session")
def temp_cosmosdb_containers() -> Iterator[CosmosDBDatabase]:
    """
    Temporary Cosmos DB containers for testing.
    """
    with temp_cosmosdb_if_emulator() as db:
        yield db


@pytest.fixture(scope="session")
def cosmosdb_containers() -> Iterator[CosmosDBDatabase]:
    """
    CosmosDBDatabase for *existing* Cosmos DB containers.

    This does not create / destroy containers. If you're relying on Azure Functions
    to run in response to Cosmos DB updates, you should ensure that the following
    environment variables are consistent between your Azure Functions container
    (started through `./scripts/server` and your test process)

    * ``PCTASKS__COSMOSDB__URL``
    * ``PCTASKS__COSMOSDB__TEST_CONTAINER_SUFFIX``

    You should also ensure that the Cosmos DB containers already exist before starting
    the Azure Functions or tests, otherwise the Azure Functions will fail to monitor
    the container.
    """
    settings = CosmosDBSettings.get()
    yield CosmosDBDatabase(settings)
