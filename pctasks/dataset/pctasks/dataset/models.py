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


class CollectionNotFoundError(Exception):
    """Raised if the requested collection is not found"""

    pass


class MultipleCollectionsError(Exception):
    """Raised if there are multiple collections in a dataset.

    The user asked for the "default" collection.
    """

    def __init__(self, dataset_id: str, collection_ids: List[str]):
        self.dataset_id = dataset_id
        self.collection_ids = collection_ids
        super().__init__(
            "Multiple collections for dataset, "
            "cannot return default collection id: "
            f"dataset={dataset_id}, "
            f"collections={collection_ids}"
        )


class SplitDefinition(PCBaseModel):
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
    splits: Optional[List[SplitDefinition]] = None

    @validator("splits")
    def _validate_splits(
        cls, v: Optional[List[SplitDefinition]]
    ) -> Optional[List[SplitDefinition]]:
        if v is None:
            return v
        _prefixes: Set[Optional[str]] = set()
        for split in v:
            if split.prefix in _prefixes:
                raise ValueError(f"Duplicate split prefix: {split.prefix}")
            _prefixes.add(split.prefix)
        return v


class StorageDefinition(PCBaseModel):
    chunks: ChunksConfig = ChunksConfig()
    uri: str
    token: Optional[str] = None

    def get_storage(self) -> Storage:
        return get_storage(self.uri, sas_token=self.token)


class CreateItemsDefinition(PCBaseModel):
    timeout: Optional[int] = None


class CollectionDefinition(PCBaseModel):
    id: str
    template: Optional[str] = None
    collection_class: str = Field(alias="class")
    asset_storage: List[StorageDefinition]
    chunk_storage: StorageDefinition
    create_items: CreateItemsDefinition = CreateItemsDefinition()

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


class DatasetDefinition(PCBaseModel):
    id: str
    image: str
    code: Optional[CodeConfig] = None
    collections: List[CollectionDefinition]
    args: Optional[List[str]] = None
    environment: Optional[Dict[str, Any]] = None
    task_config: Optional[Dict[str, Any]] = None

    def get_collection(
        self, collection_id: Optional[str] = None
    ) -> CollectionDefinition:
        if collection_id is None:
            if len(self.collections) > 1:
                raise MultipleCollectionsError(
                    self.id, [c.id for c in self.collections]
                )
            return self.collections[0]
        else:
            for collection in self.collections:
                if collection.id == collection_id:
                    return collection
            raise CollectionNotFoundError(
                f"Collection not found for dataset: "
                f"dataset={self.id}, collection_id={collection_id}"
            )

    def template_args(self, args: Dict[str, str]) -> "DatasetDefinition":
        return DictTemplater({"args": args}, strict=False).template_model(self)

    @validator("id")
    def _validate_name(cls, v: str) -> str:
        try:
            validate_table_key(v)
        except InvalidTableKeyError as e:
            raise ValueError(f"Invalid dataset id: {e.INFO_MESSAGE}")
        return v

    @validator("collections")
    def _validate_collections(
        cls, v: List[CollectionDefinition]
    ) -> List[CollectionDefinition]:
        if not v:
            raise ValueError("At least one collection must be defined for the dataset.")
        return v
