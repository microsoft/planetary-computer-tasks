import os

from pctasks.core.constants import AZURITE_HOST_ENV_VAR, AZURITE_PORT_ENV_VAR

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


AZURITE_ACCOUNT_KEY = (
    "Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6I"
    "FsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw=="
)
