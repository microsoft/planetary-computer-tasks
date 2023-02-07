"""
Azure Function to forward Blob Storage Events to the `storage-events`
container in Cosmos DB.
"""
import logging

import azure.functions as func

from pctasks.core.cosmos.containers.storage_events import StorageEventsContainer
from pctasks.core.models.event import StorageEventRecord


# TODO: use async
def main(msg: func.QueueMessage) -> None:
    logging.info("Processing message id=%s", msg.id)

    body = msg.get_body().decode("utf-8")
    event = StorageEventRecord.parse_raw(body)
    with StorageEventsContainer(StorageEventRecord) as cosmos_client:
        cosmos_client.put(event)

    logging.info("Processed message_id=%s event_id=%s", msg.id, event.id)
