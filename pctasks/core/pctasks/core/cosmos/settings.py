import os
from typing import Any, Dict, Optional
from urllib.parse import urlparse

from azure.cosmos import CosmosClient
from azure.identity import DefaultAzureCredential
from pydantic import validator

from pctasks.core.constants import COSMOSDB_EMULATOR_HOST_ENV_VAR
from pctasks.core.settings import PCTasksSettings

DEFAULT_DATABASE_NAME = "pctasks"
DEFAULT_WORKFLOW_RUNS_CONTAINER = "workflow-runs"
DEFAULT_WORKFLOWS_CONTAINER = "workflows"
DEFAULT_RECORDS_CONTAINER = "records"

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

    database: str = DEFAULT_DATABASE_NAME
    workflows_container_name: str = DEFAULT_WORKFLOWS_CONTAINER
    workflow_runs_container_name: str = DEFAULT_WORKFLOW_RUNS_CONTAINER
    records_container_name: str = DEFAULT_RECORDS_CONTAINER

    # Workflow Runs
    workflow_runs_container: str = DEFAULT_WORKFLOW_RUNS_CONTAINER

    @validator("key", always=True)  # Validates all connection properties (last defined)
    def _validate_key(cls, v: Optional[str], values: Dict[str, Any]) -> Optional[str]:
        if v:
            if values.get("connection_string"):
                raise ValueError("Cannot set both key and connection_string")
            if not values.get("url"):
                raise ValueError("Must set url when setting key")

        return v

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
            if not self.url:
                raise ValueError("Cosmos DB URL is not set")
            credential = self.key or DefaultAzureCredential()
            return CosmosClient(
                self.url, credential=credential, connection_verify=connection_verify
            )
