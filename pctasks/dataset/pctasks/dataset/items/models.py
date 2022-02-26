from typing import Any, Dict, Optional

from pydantic import validator

from pctasks.core.models.base import PCBaseModel
from pctasks.core.models.tokens import StorageAccountTokens


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
