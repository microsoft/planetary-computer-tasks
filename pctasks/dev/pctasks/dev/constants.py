import os
from typing import Dict

from pctasks.core.constants import (
    AZURITE_HOST_ENV_VAR,
    AZURITE_PORT_ENV_VAR,
    COSMOSDB_EMULATOR_HOST_ENV_VAR,
    COSMOSDB_EMULATOR_PORT_ENV_VAR,
)

TEST_DATA_CONTAINER = "test-data"

AZURITE_ACCOUNT_NAME = "devstoreaccount1"

AZURITE_CONNECTION_STRING = (
    "DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;"
    "AccountKey="
    "Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq"
    "/K1SZFPTOtr/KBHBeksoGMGw==;"
    "BlobEndpoint=http://azurite:10000/devstoreaccount1;"
    "QueueEndpoint=http://azurite:10001/devstoreaccount1;"
    "TableEndpoint=http://azurite:10002/devstoreaccount1;"
)


def get_azurite_connection_string() -> str:
    host = os.environ.get(AZURITE_HOST_ENV_VAR) or "localhost"
    blob_port = int(os.environ.get(AZURITE_PORT_ENV_VAR) or "10000")
    return (
        "DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;"
        "AccountKey="
        "Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq"
        "/K1SZFPTOtr/KBHBeksoGMGw==;"
        f"BlobEndpoint=http://{host}:{blob_port}/devstoreaccount1;"
        f"QueueEndpoint=http://{host}:{blob_port+1}/devstoreaccount1;"
        f"TableEndpoint=http://{host}:{blob_port+2}/devstoreaccount1;"
    )


def get_azurite_named_key_credential() -> Dict[str, str]:
    return {"account_name": "devstoreaccount1", "account_key": AZURITE_ACCOUNT_KEY}


AZURITE_ACCOUNT_KEY = (
    "Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6I"
    "FsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw=="
)


def get_cosmosdb_emulator_url() -> str:
    host = os.environ.get(COSMOSDB_EMULATOR_HOST_ENV_VAR) or "localhost"
    port = int(os.environ.get(COSMOSDB_EMULATOR_PORT_ENV_VAR) or "8081")

    return f"https://{host}:{port}/"


COSMOSDB_EMULATOR_ACCOUNT_KEY = (
    "C2y6yDjf5/R+ob0N8A7Cgv30VRDJIWEHLM+"
    "4QDU5DE2nQ9nDuVTqobD4b8mGGy"
    "PMbIZnqyMsEcaGQy67XIw/Jw=="
)


def get_cosmosdb_emulator_connection_string() -> str:
    return (
        f"AccountEndpoint={get_cosmosdb_emulator_url()};"
        f"AccountKey={COSMOSDB_EMULATOR_ACCOUNT_KEY};"
    )
