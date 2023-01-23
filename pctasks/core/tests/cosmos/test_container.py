from typing import Any, Dict, List, Tuple, Type

from pctasks.core.cosmos.container import AsyncCosmosDBContainer, CosmosDBContainer
from pctasks.core.cosmos.database import CosmosDBDatabase
from pctasks.core.cosmos.page import Page
from pctasks.core.models.record import Record
from pctasks.dev.cosmosdb import temp_cosmosdb_if_emulator


class MockModel(Record):
    type: str = "MOCK"
    id: str
    group_id: str = "None"
    name: str

    def get_id(self) -> str:
        return self.id


class MockContainer(CosmosDBContainer[MockModel]):
    container_name: str = "mock"
    partition_key: str = "/mock_id"

    def __init__(self, db: CosmosDBDatabase) -> None:
        self._items_to_models: List[Tuple[Dict[str, Any], MockModel]] = []
        self._models_to_items: List[Tuple[MockModel, Dict[str, Any]]] = []
        super().__init__(self.container_name, self.partition_key, MockModel, db=db)

    def get_partition_key(self, model: MockModel) -> str:
        return model.id

    def model_from_item(
        self, model_type: Type[MockModel], item: Dict[str, Any]
    ) -> MockModel:
        item.pop("mock_id", None)
        return super().model_from_item(model_type, item)

    def item_from_model(self, model: MockModel) -> Dict[str, Any]:
        item = super().item_from_model(model)
        self._items_to_models.append((item, model))
        item["mock_id"] = item["id"]
        return item


class AsyncMockContainer(AsyncCosmosDBContainer[MockModel]):
    container_name: str = "mock"
    partition_key: str = "/group_id"

    def __init__(self, db: CosmosDBDatabase) -> None:
        self._items_to_models: List[Tuple[Dict[str, Any], MockModel]] = []
        self._models_to_items: List[Tuple[MockModel, Dict[str, Any]]] = []
        super().__init__(self.container_name, self.partition_key, MockModel, db=db)

    def get_partition_key(self, model: MockModel) -> str:
        return model.id


def test_container_transforms_models():
    with temp_cosmosdb_if_emulator(
        containers={MockContainer.container_name: MockContainer.partition_key}
    ) as db:
        original = MockModel(id="1", name="one")
        container = MockContainer(db=db)
        with container:
            container.put(original)
            result = container.get(id="1", partition_key="1")

            assert result == original
            for item, model in container._items_to_models:
                assert item["mock_id"] == item["id"]
                assert item["id"] == model.id

            for model, item in container._models_to_items:
                assert item["mock_id"] == item["id"]
                assert item["id"] == model.id


async def test_container_async():
    with temp_cosmosdb_if_emulator(
        containers={AsyncMockContainer.container_name: AsyncMockContainer.partition_key}
    ) as db:
        original = MockModel(id="1", name="one", group_id="A")
        container = AsyncMockContainer(db=db)
        async with container:
            await container.put(original)
            result = await container.get(id="1", partition_key="A")

            assert result == original
            for item, model in container._items_to_models:
                assert item["mock_id"] == item["id"]
                assert item["id"] == model.id

            for model, item in container._models_to_items:
                assert item["mock_id"] == item["id"]
                assert item["id"] == model.id

            others = [
                MockModel(id=str(i), name=str(i), group_id="A") for i in range(2, 10)
            ]
            await container.bulk_put(others)

            pages: List[Page[MockModel]] = []
            async for page in container.query_paged(
                query="SELECT * FROM c where c.group_id = 'A' ",
                partition_key="A",
                page_size=2,
            ):
                pages.append(page)

            assert len(pages) == 5
