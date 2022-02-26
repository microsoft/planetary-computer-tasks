from typing import List, Optional, Tuple

from pctasks.core.models.dataset import DatasetIdentifier
from pctasks.core.tables.base import ModelTableService


class DatasetIdentifierTable(ModelTableService[DatasetIdentifier]):
    _model = DatasetIdentifier

    def _get_key(self, dataset: DatasetIdentifier) -> Tuple[str, str]:
        return (dataset.owner, dataset.name)

    def create_dataset(self, dataset: DatasetIdentifier) -> None:
        key = self._get_key(dataset)

        self.insert(partition_key=key[0], row_key=key[1], entity=dataset)

    def update_dataset(self, dataset: DatasetIdentifier) -> None:
        key = self._get_key(dataset)
        self.update(
            partition_key=key[0],
            row_key=key[1],
            entity=dataset,
        )

    def delete_dataset(self, owner: str, id: str) -> None:
        self.delete(
            partition_key=owner,
            row_key=id,
        )

    def get_dataset(self, owner: str, name: str) -> Optional[DatasetIdentifier]:
        return self.get(partition_key=owner, row_key=name)

    def get_datasets(self, owner: str) -> List[DatasetIdentifier]:
        return self.query(f"PartitionKey eq '{owner}'")
