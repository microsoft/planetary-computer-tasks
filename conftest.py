from typing import Iterator

import pytest

from pctasks.dev.cosmosdb import temp_cosmosdb_if_emulator
from pctasks.core.cosmos.database import CosmosDBDatabase


@pytest.fixture(scope="session")
def cosmosdb_containers() -> Iterator[CosmosDBDatabase]:
    """
    Temporary Cosmos DB containers for testing.
    """
    with temp_cosmosdb_if_emulator() as db:
        yield db
