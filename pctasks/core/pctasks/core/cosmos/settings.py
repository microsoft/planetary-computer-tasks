import os
import re
from typing import Any, Dict, Optional
from urllib.parse import urlparse

from azure.cosmos import CosmosClient
from azure.cosmos.aio import CosmosClient as AsyncCosmosClient
from azure.identity import DefaultAzureCredential
from pydantic import validator

from pctasks.core.constants import COSMOSDB_EMULATOR_HOST_ENV_VAR
from pctasks.core.settings import PCTasksSettings

DEFAULT_DATABASE_NAME = "pctasks"
DEFAULT_WORKFLOW_RUNS_CONTAINER = "workflow-runs"
DEFAULT_WORKFLOWS_CONTAINER = "workflows"
DEFAULT_ITEMS_CONTAINER = "items"
DEFAULT_RECORDS_CONTAINER = "records"
DEFAULT_STORAGE_EVENTS_CONTAINER_NAME = "storage-events"

DEFAULT_SINGLE_PARTITION_KEY_VALUE = "partition_key"


class CosmosDBSettingsError(Exception):
    pass


class CosmosDBSettings(PCTasksSettings):
    @classmethod
    def section_name(cls) -> str:
        return "cosmosdb"

    connection_string: Optional[str] = None
    url: Optional[str] = None
    key: Optional[str] = None

    test_container_suffix: Optional[str] = ""

    database: str = DEFAULT_DATABASE_NAME
    workflows_container_name: str = DEFAULT_WORKFLOWS_CONTAINER
    workflow_runs_container_name: str = DEFAULT_WORKFLOW_RUNS_CONTAINER
    items_container_name: str = DEFAULT_ITEMS_CONTAINER
    records_container_name: str = DEFAULT_RECORDS_CONTAINER
    storage_events_container_name: str = DEFAULT_STORAGE_EVENTS_CONTAINER_NAME

    max_bulk_put_size: int = 250

    def get_workflows_container_name(self) -> str:
        return f"{self.workflows_container_name}{self.test_container_suffix}"

    def get_workflow_runs_container_name(self) -> str:
        return f"{self.workflow_runs_container_name}{self.test_container_suffix}"

    def get_storage_events_container_name(self) -> str:
        return f"{self.storage_events_container_name}{self.test_container_suffix}"

    def get_items_container_name(self) -> str:
        return f"{self.items_container_name}{self.test_container_suffix}"

    def get_records_container_name(self) -> str:
        return f"{self.records_container_name}{self.test_container_suffix}"

    @validator("test_container_suffix", always=True)
    def _validate_test_container_suffix(cls, v: Optional[str]) -> str:
        return v or ""

    @validator("connection_string")
    def _validate_connection_string(cls, v: Optional[str]) -> Optional[str]:
        if v:
            if not re.search(r"AccountEndpoint=(.*?);", v):
                raise ValueError("Cannot find AccountEndpoint in connection_string")
            if not re.search(r"AccountKey=(.*?);", v):
                raise ValueError("Cannot find AccountKey in connection_string")
        return v

    @validator("key", always=True)  # Validates all connection properties (last defined)
    def _validate_key(cls, v: Optional[str], values: Dict[str, Any]) -> Optional[str]:
        if v:
            if values.get("connection_string"):
                raise ValueError("Cannot set both key and connection_string")
            if not values.get("url"):
                raise ValueError("Must set url when setting key")

        return v

    def ensure_valid_connection_info(self) -> None:
        if self.connection_string:
            return
        if not self.url:
            raise CosmosDBSettingsError("Must set either connection_string or url")
        if not self.key:
            if not (
                os.environ.get("AZURE_CLIENT_ID")
                and os.environ.get("AZURE_CLIENT_SECRET")
                and os.environ.get("AZURE_TENANT_ID")
            ):
                # Validate that the Azure credentials are set
                # Validation is here instead of pydantic validator
                # because we may want to get container name settings
                # without setting credentials.
                raise CosmosDBSettingsError(
                    "Must set key or connection_string, account key or "
                    "provide Azure credentials to the environment"
                )

    def get_cosmosdb_url(self) -> str:
        self.ensure_valid_connection_info()
        if self.connection_string:
            m = re.search(r"AccountEndpoint=(.*?);", self.connection_string)
            assert m  # Should be validated by pydantic
            return m.group(1)
        else:
            assert self.url
            return self.url

    def is_cosmosdb_emulator(self) -> bool:
        emulator_host = os.environ.get(COSMOSDB_EMULATOR_HOST_ENV_VAR)
        if (
            emulator_host
            and urlparse(self.get_cosmosdb_url()).hostname == emulator_host
        ):
            return True
        return False

    def get_client(self) -> CosmosClient:
        # If this is the emulator, don't verify the connection SSL cert
        connection_verify = True
        emulator_host = os.environ.get(COSMOSDB_EMULATOR_HOST_ENV_VAR)
        if emulator_host:
            if self.url:
                connection_verify = urlparse(self.url).hostname != emulator_host
            elif self.connection_string:
                connection_verify = f"//{emulator_host}:" not in self.connection_string
        if self.connection_string:
            return CosmosClient.from_connection_string(
                self.connection_string, connection_verify=connection_verify
            )
        else:
            self.ensure_valid_connection_info()
            assert self.url
            credential = self.key or DefaultAzureCredential()
            return CosmosClient(
                self.url, credential=credential, connection_verify=connection_verify
            )

    def get_async_client(self) -> AsyncCosmosClient:
        # If this is the emulator, don't verify the connection SSL cert
        connection_verify = True
        emulator_host = os.environ.get(COSMOSDB_EMULATOR_HOST_ENV_VAR)
        if emulator_host:
            if self.url:
                connection_verify = urlparse(self.url).hostname != emulator_host
            elif self.connection_string:
                connection_verify = f"//{emulator_host}:" not in self.connection_string
        if self.connection_string:
            return AsyncCosmosClient.from_connection_string(
                self.connection_string, connection_verify=connection_verify
            )
        else:
            self.ensure_valid_connection_info()
            assert self.url
            credential = self.key or DefaultAzureCredential()
            return AsyncCosmosClient(
                self.url, credential=credential, connection_verify=connection_verify
            )
