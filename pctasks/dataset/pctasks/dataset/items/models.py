from typing import Any, Dict, Optional

from pydantic import validator

from pctasks.core.models.base import PCBaseModel
from pctasks.core.models.task import TaskConfig
from pctasks.core.models.tokens import StorageAccountTokens
from pctasks.dataset.constants import CREATE_ITEMS_TASK_ID
from pctasks.dataset.models import CollectionConfig, DatasetConfig


class CreateItemsInput(PCBaseModel):
    asset_uri: Optional[str] = None
    """URI to the token asset for this Item.

    Must be specified if chunk_uri is not specified
    """

    chunk_uri: Optional[str] = None
    """Chunk to be processed containing token assets for this item.

    Must be specified if asset_path is not specified
    """

    output_uri: Optional[str] = None
    """URI to the output NDJSON file.

    Required if processing results in more than one item.
    """

    tokens: Optional[Dict[str, StorageAccountTokens]] = None
    """Optional tokens to use for accessing blob storage."""

    storage_endpoint_url: Optional[str] = None
    """Optional storage account URL to use for Azure Blob Storage.

    Used to specify emulators for local development.
    """

    limit: Optional[int] = None
    """Limit the number of items to process."""

    skip_validation: bool = False
    """Skip validation through PySTAC of the STAC Items."""

    @validator("chunk_uri")
    def validate_chunk_uri(
        cls, v: Optional[str], values: Dict[str, Any]
    ) -> Optional[str]:
        if v is None and values.get("asset_uri") is None:
            raise ValueError("Either chunk_uri or asset_uri must be specified")
        return v

    @validator("output_uri")
    def validate_output_uri(
        cls, v: Optional[str], values: Dict[str, Any]
    ) -> Optional[str]:
        if v is None and values.get("chunk_uri") is None:
            raise ValueError("output_uri must be specified if processing a chunk_uri")
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
        collection_class: str,
        args: CreateItemsInput,
        environment: Optional[Dict[str, str]] = None,
        tags: Optional[Dict[str, str]] = None,
    ) -> "CreateItemsTaskConfig":
        return CreateItemsTaskConfig(
            id=CREATE_ITEMS_TASK_ID,
            image=image,
            task=f"{collection_class}.create_items",
            args=args.dict(),
            environment=environment,
            tags=tags,
        )

    @classmethod
    def from_collection(
        cls,
        ds: DatasetConfig,
        collection: CollectionConfig,
        asset_chunk_uri: str,
        item_chunk_uri: str,
        tokens: Optional[Dict[str, StorageAccountTokens]] = None,
        storage_account_url: Optional[str] = None,
        limit: Optional[int] = None,
        skip_validation: bool = False,
        environment: Optional[Dict[str, str]] = None,
        tags: Optional[Dict[str, str]] = None,
    ) -> "CreateItemsTaskConfig":
        return cls.create(
            image=ds.image,
            collection_class=collection.collection_class,
            args=CreateItemsInput(
                chunk_uri=asset_chunk_uri,
                output_uri=item_chunk_uri,
                tokens=tokens,
                storage_endpoint_url=storage_account_url,
                limit=limit,
                skip_validation=skip_validation,
            ),
            environment=environment,
            tags=tags,
        )
