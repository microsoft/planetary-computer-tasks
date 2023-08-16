import json
import pathlib

import pytest
from pypgstac.db import PgstacDB

from pctasks.core.cosmos.containers.process_item_errors import (
    ProcessItemErrorsContainer,
)
from pctasks.core.models.event import IngestItemErrorRecord
from pctasks.core.storage import StorageFactory
from pctasks.dev.constants import get_azurite_named_key_credential
from pctasks.dev.queues import TempQueue
from pctasks.ingest.models import IngestCollectionsInput
from pctasks.ingest_task import streaming
from pctasks.ingest_task.task import IngestTask, IngestTaskInput
from pctasks.task.context import TaskContext
from pctasks.task.streaming import StreamingTaskOptions
from tests.conftest import ingest_test_environment

HERE = pathlib.Path(__file__).parent


@pytest.fixture
def document():
    """
    A document in the `items` container in Cosmos DB

    The STAC item under .data.item is a sentinel-1-grd item.
    """
    return json.loads((HERE / "items_document.json").read_text())


@pytest.fixture
def s1_grd_collection():
    return json.loads(
        (HERE / "../../../datasets/sentinel-1-grd/collection/template.json").read_text()
    )


def test_streaming_create_items_task(s1_grd_collection, document):
    # Relies on the servers running
    #   - azurite
    #   - pgstac
    context = TaskContext(run_id="test", storage_factory=StorageFactory())

    with ingest_test_environment() as conn_str_info:
        # ingest collection
        task = IngestTask()
        input = IngestTaskInput(
            content=IngestCollectionsInput(collections=[s1_grd_collection])
        )
        task.run(input, context)

        with TempQueue() as queue_client:
            # put some messages on the queue
            for _ in range(10):
                # In PublishItemsCF.__init__, we extract the item out
                # of the raw document.
                queue_client.send_message(json.dumps(document["data"]["item"]))
            task_input = streaming.StreamingIngestItemsInput(
                streaming_options=StreamingTaskOptions(
                    queue_url=queue_client.url,
                    queue_credential=get_azurite_named_key_credential(),
                    visibility_timeout=10,
                    message_limit=5,
                    resources={"limits": {}, "requests": {}},
                ),
            )

            # ingest items
            task = streaming.StreamingIngestItemsTask()
            task.run(task_input, context)

            with PgstacDB(conn_str_info.local) as db:
                results = list(
                    db.query("select * from items where collection = 'sentinel-1-grd'")
                )
            assert len(results)


def test_streaming_ingest_items_task_errors(
    s1_grd_collection,
    document,
):
    context = TaskContext(run_id="test", storage_factory=StorageFactory())

    with ingest_test_environment():
        # ingest collection
        task = IngestTask()
        input = IngestTaskInput(
            content=IngestCollectionsInput(collections=[s1_grd_collection])
        )
        task.run(input, context)

        with TempQueue() as queue_client:
            # Put some invalid JSON in the queue to simulate bad data.
            message = queue_client.send_message(
                json.dumps(document["data"]["item"]) + "not-json"
            )
            task_input = streaming.StreamingIngestItemsInput(
                streaming_options=StreamingTaskOptions(
                    queue_url=queue_client.url,
                    queue_credential=get_azurite_named_key_credential(),
                    visibility_timeout=10,
                    message_limit=1,
                    resources={"limits": {}, "requests": {}},
                ),
            )

            # ingest items
            task = streaming.StreamingIngestItemsTask()
            task.run(task_input, context)

            errors_container = ProcessItemErrorsContainer(IngestItemErrorRecord)

            record_id = f"{message.id}:test:1"
            with errors_container:
                record = errors_container.get(record_id, record_id)
                assert record is not None
                assert record.run_id == "test"
                assert record.attempt == 1
                assert "JSONDecodeError" in record.traceback
