from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Union

from pydantic import Field, validator

from pctasks.core.models.base import PCBaseModel
from pctasks.core.models.config import CodeConfig
from pctasks.core.models.tokens import ContainerTokens, StorageAccountTokens
from pctasks.core.storage import get_storage
from pctasks.core.storage.base import Storage
from pctasks.core.storage.blob import BlobUri
from pctasks.core.tables.base import InvalidTableKeyError, validate_table_key
from pctasks.core.utils.template import DictTemplater
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
        _prefixes: Set[Optional[str]] = set()
        for split in v:
            if split.prefix in _prefixes:
                raise ValueError(f"Duplicate split prefix: {split.prefix}")
            _prefixes.add(split.prefix)
        return v


class StorageConfig(PCBaseModel):
    chunks: ChunksConfig = ChunksConfig()
    uri: str
    token: Optional[str] = None

    def get_storage(self) -> Storage:
        return get_storage(self.uri, sas_token=self.token)


class CollectionConfig(PCBaseModel):
    id: str
    template: Optional[str] = None
    collection_class: str = Field(alias="class")
    asset_storage: List[StorageConfig]
    chunk_storage: StorageConfig

    def get_tokens(self) -> Dict[str, StorageAccountTokens]:
        """Collects SAS tokens from any container configs."""
        tokens: Dict[str, StorageAccountTokens] = {}
        containers = self.asset_storage + [self.chunk_storage]
        for container in containers:
            if container.token:
                if BlobUri.matches(container.uri):
                    blob_uri = BlobUri(container.uri)
                    if blob_uri.storage_account_name not in tokens:
                        tokens[blob_uri.storage_account_name] = StorageAccountTokens(
                            containers={}
                        )
                    container_tokens = tokens[blob_uri.storage_account_name].containers
                    assert container_tokens is not None
                    container_tokens[blob_uri.container_name] = ContainerTokens(
                        token=container.token
                    )

        return tokens

    class Config:
        allow_population_by_field_name = True


class DatasetConfig(PCBaseModel):
    id: str
    image: str
    code: Optional[CodeConfig] = None
    collections: List[CollectionConfig]
    args: Optional[List[str]] = None
    environment: Optional[Dict[str, Any]] = None

    def get_collection(self, collection_id: Optional[str] = None) -> CollectionConfig:
        if collection_id is None:
            if len(self.collections) > 1:
                raise MultipleCollections(
                    "Multiple collections for dataset, "
                    "cannot return default collection id: "
                    f"dataset={self.id}, "
                    f"collections={[c.id for c in self.collections]}"
                )
            return self.collections[0]
        else:
            for collection in self.collections:
                if collection.id == collection_id:
                    return collection
            raise CollectionNotFound(
                f"Collection not found for dataset: "
                f"dataset={self.id}, collection_id={collection_id}"
            )

    def template_args(self, args: Dict[str, str]) -> "DatasetConfig":
        return DictTemplater({"args": args}, strict=False).template_model(self)

    @validator("id")
    def _validate_name(cls, v: str) -> str:
        try:
            validate_table_key(v)
        except InvalidTableKeyError as e:
            raise ValueError(f"Invalid dataset id: {e.INFO_MESSAGE}")
        return v

    @validator("collections")
    def _validate_collections(cls, v: List[CollectionConfig]) -> List[CollectionConfig]:
        if not v:
            raise ValueError("At least one collection must be defined for the dataset.")
        return v
