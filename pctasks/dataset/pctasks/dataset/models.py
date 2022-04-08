import os
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Union

from pydantic import Field, validator

from pctasks.core.constants import MICROSOFT_OWNER
from pctasks.core.models.base import PCBaseModel
from pctasks.core.models.dataset import DatasetIdentifier
from pctasks.core.models.tokens import ContainerTokens, StorageAccountTokens
from pctasks.core.storage import get_storage
from pctasks.core.storage.base import Storage
from pctasks.core.tables.base import InvalidTableKeyError, validate_table_key
from pctasks.dataset.constants import DEFAULT_CHUNK_LENGTH


class CollectionNotFound(Exception):
    """Raised if the requested collection is not found"""

    pass


class MultipleCollections(Exception):
    """Raised if there are multiple collections in a dataset.

    The user asked for the "default" collection.
    """

    pass


class SplitConfig(PCBaseModel):
    """Configuration for a split task for a single URI."""

    prefix: Optional[str] = None
    depth: int


class ChunksConfig(PCBaseModel):
    length: int = DEFAULT_CHUNK_LENGTH
    ext: Optional[str] = None
    name_starts_with: Optional[str] = None
    splits: Optional[List[SplitConfig]] = None

    @validator("splits")
    def _validate_splits(
        cls, v: Optional[List[SplitConfig]]
    ) -> Optional[List[SplitConfig]]:
        if v is None:
            return v
        paths = set()
        for split in v:
            if split.prefix in paths:
                raise ValueError(f"Duplicate split prefix: {split.prefix}")
            paths.add(split.prefix)
        return v


class StorageConfig(PCBaseModel, ABC):
    chunks: ChunksConfig = ChunksConfig()

    @abstractmethod
    def get_uri(self, path: Optional[str] = None) -> str:
        pass

    @abstractmethod
    def get_storage(self) -> Storage:
        pass


class BlobStorageConfig(StorageConfig):
    storage_account: str
    container: str
    prefix: Optional[str] = None
    sas_token: Optional[str] = None

    def get_uri(self, path: Optional[str] = None) -> str:
        uri = f"blob://{self.storage_account}/{self.container}"
        if self.prefix:
            uri = os.path.join(uri, self.prefix)
        if path:
            uri = os.path.join(uri, path)
        return uri

    def get_storage(self) -> Storage:
        return get_storage(self.get_uri(), sas_token=self.sas_token)


class LocalStorageConfig(StorageConfig):
    path: str

    def get_uri(self, path: Optional[str] = None) -> str:
        if path:
            return os.path.join(self.path, path)
        return self.path

    def get_storage(self) -> Storage:
        return get_storage(self.path)


class CollectionConfig(PCBaseModel):
    id: str
    collection_class: str = Field(alias="class")
    asset_storage: List[Union[BlobStorageConfig, LocalStorageConfig]]
    chunk_storage: Union[BlobStorageConfig, LocalStorageConfig]
    item_storage: Union[BlobStorageConfig, LocalStorageConfig]

    def get_tokens(self) -> Dict[str, StorageAccountTokens]:
        """Collects SAS tokens from any container configs."""
        tokens: Dict[str, StorageAccountTokens] = {}
        containers = self.asset_storage + [self.chunk_storage]
        if self.item_storage:
            containers.append(self.item_storage)
        for container in containers:
            if isinstance(container, BlobStorageConfig):
                if container.sas_token:
                    if container.storage_account not in tokens:
                        tokens[container.storage_account] = StorageAccountTokens(
                            containers={}
                        )
                    container_tokens = tokens[container.storage_account].containers
                    assert container_tokens is not None
                    container_tokens[container.container] = ContainerTokens(
                        token=container.sas_token
                    )
        return tokens

    class Config:
        allow_population_by_field_name = True


class DatasetConfig(DatasetIdentifier):
    owner: str = MICROSOFT_OWNER
    name: str
    image: str
    collections: List[CollectionConfig]

    def get_collection(self, collection_id: Optional[str] = None) -> CollectionConfig:
        if collection_id is None:
            if len(self.collections) > 1:
                raise MultipleCollections(
                    "Multiple collections for dataset, "
                    "cannot return default collection id: "
                    f"dataset={self.name}, "
                    f"collections={[c.id for c in self.collections]}"
                )
            return self.collections[0]
        else:
            for collection in self.collections:
                if collection.id == collection_id:
                    return collection
            raise CollectionNotFound(
                f"Collection not found for dataset: "
                f"dataset={self.name}, collection_id={collection_id}"
            )

    def get_identifier(self) -> DatasetIdentifier:
        return DatasetIdentifier(owner=self.owner, name=self.name)

    @validator("name")
    def _validate_name(cls, v: str) -> str:
        try:
            validate_table_key(v)
        except InvalidTableKeyError as e:
            raise ValueError(f"Invalid dataset name: {e.INFO_MESSAGE}")
        return v

    @validator("collections")
    def _validate_collections(cls, v: List[CollectionConfig]) -> List[CollectionConfig]:
        if not v:
            raise ValueError("At least one collection must be defined for the dataset.")
        return v
