from datetime import datetime
from typing import Dict, List, Optional

from pctasks.core.models.base import PCBaseModel
from pctasks.core.models.dataset import DatasetIdentifier
from pctasks.core.models.task import TaskConfig
from pctasks.core.models.tokens import StorageAccountTokens
from pctasks.core.models.workflow import JobConfig, WorkflowConfig
from pctasks.core.storage import get_storage
from pctasks.core.storage.base import Storage
from pctasks.dataset.chunks.constants import CREATE_CHUNKS_TASK_PATH
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

    chunk_length: int
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

    chunk_prefix: str = "uris-list-"
    """Prefix for the chunk file names."""

    chunk_extension: str = ".csv"
    """Extensions of the chunk file names."""

    def get_src_storage(self) -> Storage:
        return get_storage(self.src_storage_uri, sas_token=self.src_sas)

    def get_dst_storage(self) -> Storage:
        return get_storage(self.dst_storage_uri, sas_token=self.dst_sas)


class CreateChunksOutput(PCBaseModel):
    chunk_uris: List[str]
    """List of URIs to chunk files that each contain a lists of asset URIs."""


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


class CreateChunksWorkflowConfig(WorkflowConfig):
    @classmethod
    def create(
        cls,
        image: str,
        dataset: DatasetIdentifier,
        collection_id: str,
        args: CreateChunksInput,
        group_id: Optional[str] = None,
        tokens: Optional[Dict[str, StorageAccountTokens]] = None,
        environment: Optional[Dict[str, str]] = None,
        tags: Optional[Dict[str, str]] = None,
    ) -> "CreateChunksWorkflowConfig":
        task = CreateChunksTaskConfig.create(
            image=image, args=args, environment=environment, tags=tags
        )

        return CreateChunksWorkflowConfig(
            dataset=dataset,
            group_id=group_id,
            name=f"Create Chunks for {collection_id}",
            tokens=tokens,
            jobs={"chunks": JobConfig(tasks=[task])},
        )
