import os
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import Field, validator

from pctasks.core.constants import MICROSOFT_OWNER
from pctasks.core.models.base import PCBaseModel
from pctasks.core.models.dataset import DatasetIdentifier
from pctasks.core.models.tokens import ContainerTokens, StorageAccountTokens
from pctasks.core.storage import get_storage
from pctasks.core.storage.base import Storage
from pctasks.core.storage.blob import BlobUri
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


class ChunkOptions(PCBaseModel):
    chunk_length: Union[int, str] = DEFAULT_CHUNK_LENGTH
    """Length of each chunk. Each chunk file will contain at most this many uris."""

    name_starts_with: Optional[str] = None
    """Only include asset URIs that start with this string."""

    since: Optional[datetime] = None
    """Only include assets that have been modified since this time."""

    extensions: Optional[List[str]] = None
    """Only include asset URIs with an extension in this list."""

    ends_with: Optional[str] = None
    """Only include asset URIs that end with this string."""

    matches: Optional[str] = None
    """Only include asset URIs that match this regex."""

    limit: Optional[int] = None
    """Limit the number of URIs to process. """

    max_depth: Optional[int] = None
    """Maximum number of directories to descend into."""

    list_folders: Optional[bool] = False
    """Whether to list files (the default) or folders instead of files."""

    chunk_file_name: str = "uris-list"
    """Chunk file name."""

    chunk_extension: str = ".csv"
    """Extensions of the chunk file names."""

    def get_chunk_length(self) -> int:
        try:
            return int(self.chunk_length)
        except ValueError:
            raise ValueError(
                f"chunk_length must be an integer. Got {self.chunk_length}."
            )


class ChunksConfig(PCBaseModel):
    options: ChunkOptions = ChunkOptions()
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

    @abstractmethod
    def matches(self, uri: str) -> bool:
        """Returns True if the uri is a valid uri for this storage config."""
        pass


class BlobStorageConfig(StorageConfig):
    # TODO: Just use URI, don't differentiate between local and blob
    # (sas_token optional)
    storage_account: Optional[str] = None
    container: Optional[str] = None
    uri: Optional[str]
    prefix: Optional[str] = None
    sas_token: Optional[str] = None

    def get_uri(self, path: Optional[str] = None) -> str:
        if self.uri:
            return self.uri
        uri = f"blob://{self.storage_account}/{self.container}"
        if self.prefix:
            uri = os.path.join(uri, self.prefix)
        if path:
            uri = os.path.join(uri, path)
        return uri

    def get_storage(self) -> Storage:
        return get_storage(self.get_uri(), sas_token=self.sas_token)

    def matches(self, uri: str) -> bool:
        if self.uri:
            return uri.startswith(self.uri)

        if BlobUri.matches(uri):
            blob_uri = BlobUri(uri)
            if blob_uri.storage_account_name == self.storage_account:
                if blob_uri.container_name == self.container:
                    if self.prefix:
                        return (
                            blob_uri.blob_name is not None
                            and blob_uri.blob_name.startswith(self.prefix)
                        )
                    else:
                        return True
        return False


class LocalStorageConfig(StorageConfig):
    path: str

    def get_uri(self, path: Optional[str] = None) -> str:
        if path:
            return os.path.join(self.path, path)
        return self.path

    def get_storage(self) -> Storage:
        return get_storage(self.path)

    def matches(self, uri: str) -> bool:
        return uri.startswith(self.path)


class CollectionConfig(PCBaseModel):
    id: str
    collection_class: str = Field(alias="class")
    asset_storage: List[Union[BlobStorageConfig, LocalStorageConfig]]
    chunk_storage: Union[BlobStorageConfig, LocalStorageConfig]

    def get_tokens(self) -> Dict[str, StorageAccountTokens]:
        """Collects SAS tokens from any container configs."""
        tokens: Dict[str, StorageAccountTokens] = {}
        containers = self.asset_storage + [self.chunk_storage]
        for container in containers:
            if isinstance(container, BlobStorageConfig):
                if container.sas_token:
                    if BlobUri.matches(container.get_uri()):
                        blob_uri = BlobUri(container.get_uri())
                        if blob_uri.storage_account_name not in tokens:
                            tokens[
                                blob_uri.storage_account_name
                            ] = StorageAccountTokens(containers={})
                        container_tokens = tokens[
                            blob_uri.storage_account_name
                        ].containers
                        assert container_tokens is not None
                        container_tokens[blob_uri.container_name] = ContainerTokens(
                            token=container.sas_token
                        )
        return tokens

    def get_storage_config(
        self, uri: str
    ) -> Union[BlobStorageConfig, LocalStorageConfig]:
        for storage in self.asset_storage:
            if storage.matches(uri):
                return storage
        raise ValueError(f"No storage config found that matches {uri}")

    class Config:
        allow_population_by_field_name = True


class DatasetConfig(DatasetIdentifier):
    owner: str = MICROSOFT_OWNER
    name: str
    image: str
    code: Optional[str] = None
    collections: List[CollectionConfig]
    args: Optional[List[str]] = None
    environment: Optional[Dict[str, Any]] = None

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
