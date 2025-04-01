"""
Azure Function to forward Blob Storage Events to the `storage-events`
container in Cosmos DB.
"""

import json
import logging

import azure.functions as func

from pctasks.core.cosmos.containers.storage_events import StorageEventsContainer
from pctasks.core.models.event import StorageEventRecord


# TODO: use async
def main(msg: func.QueueMessage) -> None:
    body = msg.get_body().decode("utf-8")
    event = StorageEventRecord.model_validate_json(body)
    with StorageEventsContainer(StorageEventRecord) as cosmos_client:
        cosmos_client.put(event)

    # Azure Functions overwrites custom_dimensions so we stuff the
    # structured log record into the "message" field.
    # https://github.com/Azure/azure-functions-python-worker/issues/694
    message = {
        "message": "Processed message",
        "type": "storage-event",
        "message_id": msg.id,
        "event_id": event.id,
        "url": event.data.url,
    }

    logging.info(json.dumps(message))
