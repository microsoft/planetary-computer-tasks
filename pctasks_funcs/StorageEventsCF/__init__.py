# import base64
# import binascii
import os
import json
import logging

import azure.functions as func
import azure.cosmos
import azure.identity


# TODO: setup config, remove fallbacks
# TODO: key credential for azurite
# TODO: figure out when the message body is base64 encoded.

COSMOS_ENDPOINT = os.environ.get(
    "PCTASKS_COSMOS_ENDPOINT" "https://pclowlatencytesttom.documents.azure.com:443/"
)
DB_NAME = os.environ.get("PCTASKS_COSMOS_DATABASE_NAME" "lowlatencydb")
CONTAINER_NAME = os.environ.get("PCTASKS_COSMOS_CONTAINER_NAME" "storage-events")


def main(msg: func.QueueMessage):
    credential = azure.identity.DefaultAzureCredential()
    client = azure.cosmos.CosmosClient(COSMOS_ENDPOINT, credential)
    logging.info.info("Processing message id=%s", msg.id)

    body = msg.get_body()

    try:
        event = json.loads(body)
    except json.JSONDecodeError:
        logging.exception("Message=%s body is not valid JSON", body)
        raise

    (
        client.get_database_client(DB_NAME)
        .get_container_client(CONTAINER_NAME)
        .upsert_item(event)
    )
    logging.info("Processed message_id=%s event_id=%s", msg.id, event["id"])


if __name__ == "__main__":
    main()
