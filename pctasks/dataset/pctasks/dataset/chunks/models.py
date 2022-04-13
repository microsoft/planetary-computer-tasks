from typing import Dict, List, Optional, Union
from pctasks.dataset.models import (
    BlobStorageConfig,
    ChunkOptions,
    CollectionConfig,
    DatasetConfig,
)

from pctasks.core.models.base import PCBaseModel
from pctasks.core.models.task import TaskConfig
from pctasks.core.storage import get_storage
from pctasks.core.storage.base import Storage
from pctasks.dataset.chunks.constants import (
    ALL_CHUNK_PREFIX,
    ASSET_CHUNKS_PREFIX,
    CREATE_CHUNKS_TASK_PATH,
)
from pctasks.dataset.constants import LIST_FILES_TASK_ID


class CreateChunksInput(PCBaseModel):
    src_storage_uri: str
    """Storage URI for the source assets to be chunked."""
    src_sas: Optional[str] = None
    """SAS Token to access the source container, if URI is to blob storage."""

    dst_storage_uri: str
    """Storage URI for where the chunks should be saved."""

    dst_sas: Optional[str] = None
    """SAS Token to access the source container, if URI is to blob storage."""

    options: Union[str, ChunkOptions] = ChunkOptions()

    def get_src_storage(self) -> Storage:
        return get_storage(self.src_storage_uri, sas_token=self.src_sas)

    def get_dst_storage(self) -> Storage:
        return get_storage(self.dst_storage_uri, sas_token=self.dst_sas)


class ChunkInfo(PCBaseModel):
    uri: str
    """URI of the chunk."""
    chunk_id: str
    """ID of the chunk."""


class CreateChunksOutput(PCBaseModel):
    chunks: List[ChunkInfo]
    """List of chunks. Each chunk contain a lists of asset URIs."""


class CreateChunksTaskConfig(TaskConfig):
    @classmethod
    def create(
        cls,
        image: str,
        args: CreateChunksInput,
        environment: Optional[Dict[str, str]] = None,
        tags: Optional[Dict[str, str]] = None,
    ) -> "CreateChunksTaskConfig":
        return CreateChunksTaskConfig(
            id=LIST_FILES_TASK_ID,
            image=image,
            args=args.dict(),
            task=CREATE_CHUNKS_TASK_PATH,
            environment=environment,
            tags=tags,
        )

    @classmethod
    def from_collection(
        cls,
        ds: DatasetConfig,
        collection: CollectionConfig,
        chunkset_id: str,
        src_storage_uri: str,
        src_sas: Optional[str] = None,
        options: Optional[Union[str, ChunkOptions]] = None,
        environment: Optional[Dict[str, str]] = None,
        tags: Optional[Dict[str, str]] = None,
    ) -> "CreateChunksTaskConfig":
        chunk_storage_config = collection.chunk_storage
        assets_chunk_folder = f"{chunkset_id}/{ASSET_CHUNKS_PREFIX}/{ALL_CHUNK_PREFIX}"
        dst_storage_uri = chunk_storage_config.get_uri(assets_chunk_folder)
        dst_sas: Optional[str] = None
        if isinstance(chunk_storage_config, BlobStorageConfig):
            dst_sas = chunk_storage_config.sas_token

        return cls.create(
            image=ds.image,
            args=CreateChunksInput(
                src_storage_uri=src_storage_uri,
                src_sas=src_sas,
                dst_storage_uri=dst_storage_uri,
                dst_sas=dst_sas,
                options=options or ChunkOptions(),
            ),
            environment=environment,
            tags=tags,
        )
