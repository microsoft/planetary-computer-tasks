from typing import Any, Dict, List, Tuple, Type

from pctasks.core.cosmos.container import CosmosDBContainer
from pctasks.core.cosmos.database import CosmosDBDatabase
from pctasks.core.models.record import Record
from pctasks.dev.cosmosdb import temp_cosmosdb_if_emulator


class MockModel(Record):
    type: str = "MOCK"
    id: str
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
