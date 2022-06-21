from typing import Any, Dict, Optional

import azure.storage.blob
from cachetools import Cache, LRUCache, cachedmethod
from pydantic import Field, validator

from pctasks.core.constants import DEFAULT_DATASET_TABLE_NAME
from pctasks.core.models.base import PCBaseModel
from pctasks.core.models.config import ImageConfig
from pctasks.core.settings import PCTasksSettings
from pctasks.core.storage.blob import BlobStorage
from pctasks.core.tables.dataset import DatasetIdentifierTable


class TablesConfig(PCBaseModel):
    """Configuration for accessing tables.

    This is a temporary solution until we can fit
    a REST API in front of PCTasks.
    """

    _cache: Cache = LRUCache(maxsize=100)

    connection_string: str
    dataset_table_name: str = DEFAULT_DATASET_TABLE_NAME

    @cachedmethod(lambda self: self._cache, key=lambda self: self.dataset_table_name)
    def get_dataset_table(self) -> DatasetIdentifierTable:
        return DatasetIdentifierTable.from_connection_string(
            connection_string=self.connection_string,
            table_name=self.dataset_table_name,
        )


class SubmitSettings(PCTasksSettings):
    @classmethod
    def section_name(cls) -> str:
        return "submit"

    account_url: Optional[str] = None
    connection_string: Optional[str] = None
    account_key: Optional[str] = None
    sas_token: Optional[str] = None
    queue_name: str
    image_keys: Dict[str, ImageConfig] = Field(default_factory=dict)

    tables: Optional[TablesConfig] = None

    @validator("sas_token", always=True)
    def sas_token_validator(
        cls, v: Optional[str], values: Dict[str, Any]
    ) -> Optional[str]:
        account_url = values["account_url"]
        account_key = values["account_key"]
        connection_string = values["connection_string"]
        if v is not None and account_url is None:
            raise ValueError("Must specify account_url if supplying sas_token.")
        if not (v or account_key or connection_string):
            raise ValueError(
                "Must specify one of: account_key, sas_token, connection_string."
            )

        return v

    def get_submit_queue_url(self) -> str:
        if not self.account_url:
            raise ValueError("account_url is not set.")
        return self.account_url

    def get_storage(self, container_name: str) -> BlobStorage:
        # Hack: get the "code" blob storage container associated with
        # this storage queue. In the future, we'll have an API for
        # submitting code.
        if self.connection_string:
            storage = BlobStorage.from_connection_string(
                self.connection_string,
                container_name,
            )
        elif self.account_url and self.account_key:
            container_client = azure.storage.blob.ContainerClient(
                account_url=self.account_url.replace(".queue.", ".blob."),
                container_name=container_name,
                credential=self.account_key,
            )
            account_url = container_client.primary_endpoint.rsplit("/", 1)[0]
            blob_uri = (
                f"blob://{container_client.credential.account_name}/{container_name}"
            )

            storage = BlobStorage.from_account_key(
                account_key=self.account_key,
                account_url=account_url,
                blob_uri=blob_uri,
            )
        else:
            # probably not reachable
            raise RuntimeError("No storage configuration in settings file")
        return storage
