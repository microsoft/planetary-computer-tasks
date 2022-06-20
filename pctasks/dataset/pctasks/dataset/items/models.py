from typing import Any, Dict, Optional

from pydantic import validator

from pctasks.core.models.base import PCBaseModel
from pctasks.core.models.task import TaskConfig
from pctasks.dataset.chunks.constants import ITEM_CHUNKS_PREFIX
from pctasks.dataset.chunks.models import ChunkInfo
from pctasks.dataset.constants import CREATE_ITEMS_TASK_ID
from pctasks.dataset.models import CollectionConfig, DatasetConfig


class CreateItemsOptions(PCBaseModel):
    limit: Optional[int] = None
    """Limit the number of items to process."""

    skip_validation: bool = False
    """Skip validation through PySTAC of the STAC Items."""


class CreateItemsInput(PCBaseModel):
    asset_uri: Optional[str] = None
    """URI to the token asset for this Item.

    Must be specified if chunk_uri is not specified
    """

    asset_chunk_info: Optional[ChunkInfo] = None

    item_chunkset_uri: Optional[str] = None
    """URI to the NDJSON chunkset.

    Required if processing results in more than one item.
    """

    options: CreateItemsOptions = CreateItemsOptions()

    @validator("asset_chunk_info")
    def _validate_chunk_uri(
        cls, v: Optional[str], values: Dict[str, Any]
    ) -> Optional[str]:
        if v is None and values.get("asset_uri") is None:
            raise ValueError("Either asset_chunk_info or asset_uri must be specified")
        return v

    @validator("item_chunkset_uri")
    def _validate_output_uri(
        cls, v: Optional[str], values: Dict[str, Any]
    ) -> Optional[str]:
        if v is None and values.get("asset_chunk_info") is None:
            raise ValueError(
                "item_chunkset_uri must be specified if not processing asset_chunk_info"
            )
        return v


class CreateItemsOutput(PCBaseModel):
    item: Optional[Dict[str, Any]] = None
    """The created item."""

    ndjson_uri: Optional[str] = None
    """List of URIs to items."""

    @validator("ndjson_uri")
    def validate_uris(cls, v: Optional[str], values: Dict[str, Any]) -> Optional[str]:
        if not v:
            if not values.get("item"):
                raise ValueError("Must specify either ndjson_uri or item")
        else:
            if values.get("item"):
                raise ValueError("Must specify either ndjson_uri or item")
        return v


class CreateItemsTaskConfig(TaskConfig):
    @classmethod
    def create(
        cls,
        image: str,
        code: str,
        collection_class: str,
        args: CreateItemsInput,
        environment: Optional[Dict[str, str]] = None,
        tags: Optional[Dict[str, str]] = None,
    ) -> "CreateItemsTaskConfig":
        return CreateItemsTaskConfig(
            id=CREATE_ITEMS_TASK_ID,
            image=image,
            code=code,
            task=f"{collection_class}.create_items_task",
            args=args.dict(),
            environment=environment,
            tags=tags,
        )

    @classmethod
    def from_collection(
        cls,
        ds: DatasetConfig,
        collection: CollectionConfig,
        chunkset_id: str,
        asset_chunk_info: ChunkInfo,
        options: Optional[CreateItemsOptions] = None,
        environment: Optional[Dict[str, str]] = None,
        tags: Optional[Dict[str, str]] = None,
    ) -> "CreateItemsTaskConfig":
        chunk_storage_config = collection.chunk_storage
        items_chunk_folder = f"{chunkset_id}/{ITEM_CHUNKS_PREFIX}"

        return cls.create(
            image=ds.image,
            code=ds.code,
            collection_class=collection.collection_class,
            args=CreateItemsInput(
                asset_chunk_info=asset_chunk_info,
                item_chunkset_uri=chunk_storage_config.get_uri(items_chunk_folder),
                options=options or CreateItemsOptions(),
            ),
            environment=environment,
            tags=tags,
        )
