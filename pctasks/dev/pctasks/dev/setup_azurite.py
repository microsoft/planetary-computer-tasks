#!/bin/bash
"""
Sets up the Azurite development environment.
Meant to execute in a pctasks development docker container.
"""
from azure.data.tables import TableServiceClient
from azure.storage.blob import BlobServiceClient
from azure.storage.queue import QueueServiceClient

from pctasks.core.constants import (
    DEFAULT_BLOB_TRIGGER_REGISTRATION_TABLE_NAME,
    DEFAULT_CODE_CONTAINER,
    DEFAULT_DATASET_TABLE_NAME,
    DEFAULT_IMAGE_KEY_TABLE_NAME,
    DEFAULT_INBOX_QUEUE_NAME,
    DEFAULT_JOB_RUN_RECORD_TABLE_NAME,
    DEFAULT_LOG_CONTAINER,
    DEFAULT_NOTIFICATIONS_QUEUE_NAME,
    DEFAULT_OPERATIONS_QUEUE_NAME,
    DEFAULT_SIGNAL_QUEUE_NAME,
    DEFAULT_TASK_IO_CONTAINER,
    DEFAULT_TASK_RUN_RECORD_TABLE_NAME,
    DEFAULT_WORKFLOW_QUEUE_NAME,
    DEFAULT_WORKFLOW_RUN_GROUP_RECORD_TABLE_NAME,
    DEFAULT_WORKFLOW_RUN_RECORD_TABLE_NAME,
)
from pctasks.core.models.config import ImageConfig
from pctasks.core.tables.config import ImageKeyEntryTable
from pctasks.dev.constants import TEST_DATA_CONTAINER, get_azurite_connection_string


def setup_azurite() -> None:

    # Queues

    print("~ Setting up queues...")

    queue_client = QueueServiceClient.from_connection_string(
        get_azurite_connection_string()
    )
    existing_queues = [q.name for q in queue_client.list_queues()]
    for queue_name in [
        DEFAULT_WORKFLOW_QUEUE_NAME,
        DEFAULT_INBOX_QUEUE_NAME,
        DEFAULT_NOTIFICATIONS_QUEUE_NAME,
        DEFAULT_SIGNAL_QUEUE_NAME,
        DEFAULT_OPERATIONS_QUEUE_NAME,
    ]:
        if queue_name not in existing_queues:
            print(f"~ ~ Creating {queue_name} queue...")
            queue_client.create_queue(queue_name)

    # Tables

    print("~ Setting up tables...")

    table_service_client = TableServiceClient.from_connection_string(
        get_azurite_connection_string()
    )
    tables = [t.name for t in table_service_client.list_tables()]
    for table in [
        DEFAULT_DATASET_TABLE_NAME,
        DEFAULT_WORKFLOW_RUN_GROUP_RECORD_TABLE_NAME,
        DEFAULT_WORKFLOW_RUN_RECORD_TABLE_NAME,
        DEFAULT_JOB_RUN_RECORD_TABLE_NAME,
        DEFAULT_TASK_RUN_RECORD_TABLE_NAME,
        DEFAULT_IMAGE_KEY_TABLE_NAME,
        DEFAULT_BLOB_TRIGGER_REGISTRATION_TABLE_NAME,
    ]:
        if table not in tables:
            print(f"~ ~ Creating table {table}...")
            table_service_client.create_table(table)

    with ImageKeyEntryTable(
        lambda: (
            None,
            table_service_client.get_table_client(DEFAULT_IMAGE_KEY_TABLE_NAME),
        )
    ) as image_key_table:
        image_key_table.set_image(
            "ingest",
            image_config=ImageConfig(
                image="pc-ingest:latest",
                environment=[
                    "DB_CONNECTION_STRING=${{ secrets.DB_CONNECTION_STRING }}",
                ],
            ),
        )

    # Blobs

    print("~ Setting up blob storage...")

    blob_service_client: BlobServiceClient = BlobServiceClient.from_connection_string(
        get_azurite_connection_string()
    )
    containers = [c.name for c in blob_service_client.list_containers()]
    for container in [
        DEFAULT_LOG_CONTAINER,
        DEFAULT_TASK_IO_CONTAINER,
        DEFAULT_CODE_CONTAINER,
        TEST_DATA_CONTAINER,
    ]:
        if container not in containers:
            print(f"~ ~ Creating container {container}...")
            blob_service_client.create_container(container)

    print("~ Done Azurite setup.")


if __name__ == "__main__":
    setup_azurite()
