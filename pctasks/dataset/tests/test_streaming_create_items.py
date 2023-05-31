import datetime
import json
import logging
import os
import pathlib

import azure.storage.queue
import pystac
import pytest

from pctasks.core.constants import (
    AZURITE_HOST_ENV_VAR,
    AZURITE_PORT_ENV_VAR,
    AZURITE_STORAGE_ACCOUNT_ENV_VAR,
)
from pctasks.core.models.event import StorageEventData
from pctasks.core.storage import StorageFactory
from pctasks.dataset import streaming
from pctasks.dev.azurite import setup_azurite
from pctasks.dev.blob import temp_azurite_blob_storage
from pctasks.dev.constants import get_azurite_named_key_credential
from pctasks.dev.queues import TempQueue
from pctasks.task.context import TaskContext
from pctasks.task.streaming import StreamingTaskOptions

HERE = pathlib.Path(__file__).parent

BLANK_ITEM = pystac.Item(
    "id",
    geometry={"type": "Point", "coordinates": [0, 0]},
    bbox=[0, 0, 0, 0],
    datetime=datetime.datetime(2000, 1, 1),
    properties={},
)


class CreateItems:
    def __init__(self):
        self.count = 0

    def __call__(self, asset_uri, storage_factory):
        self.count += 1
        result = BLANK_ITEM.full_copy()
        return [result]


class BuggyCreateItems:
    def __init__(self):
        self.count = 0

    def __call__(self, asset_uri, storage_factory):
        self.count += 1
        raise ZeroDivisionError(asset_uri)


@pytest.fixture
def storage_event():
    return json.loads((HERE / "data-files/storage-event.json").read_text())


def test_process_message(storage_event):
    task = streaming.StreamingCreateItemsTask()
    create_items = CreateItems()
    message = azure.storage.queue.QueueMessage(content=json.dumps(storage_event))
    context = TaskContext(run_id="test", storage_factory=StorageFactory())
    task_input = streaming.StreamingCreateItemsInput(
        collection_id="test",
        create_items_function=create_items,
        streaming_options=StreamingTaskOptions(
            # process_message doesn't actually touch the queue
            queue_url="http://example.com",
            queue_credential=get_azurite_named_key_credential(),
            visibility_timeout=9,
            message_limit=5,
        ),
    )
    extra_options = task.get_extra_options(task_input, context)
    ok, err = task.process_message(
        message,
        task_input,
        context,
        extra_options=extra_options,
    )
    assert err is None
    assert len(ok) == 1
    item = ok[0]
    assert item.id
    assert item.collection_id


@pytest.mark.usefixtures("temp_cosmosdb_containers")
def test_streaming_create_items_task(storage_event):
    # This implicitly uses
    # - azurite for queues
    task = streaming.StreamingCreateItemsTask()
    create_items = CreateItems()

    with TempQueue(
        message_decode_policy=None, message_encode_policy=None
    ) as queue_client:
        # put some messages on the queue
        storage_event["data"]["url"] = "test.tif"
        storage_event["time"] = "2023-03-27T21:12:27.7409548Z"
        for _ in range(10):
            queue_client.send_message(json.dumps(storage_event))
        task_input = streaming.StreamingCreateItemsInput(
            collection_id="test",
            create_items_function=create_items,
            streaming_options=StreamingTaskOptions(
                queue_url=queue_client.url,
                queue_credential=get_azurite_named_key_credential(),
                visibility_timeout=10,
                message_limit=5,
            ),
        )
        context = TaskContext(run_id="test", storage_factory=StorageFactory())
        task.run(task_input, context)
        assert create_items.count == 10
        assert queue_client.get_queue_properties().approximate_message_count == 0


def test_streaming_create_items_from_message(storage_event):
    task = streaming.StreamingCreateItemsTask()

    class MyCreateItems:
        def __init__(self):
            self.items = []

        def __call__(self, asset_uri, storage_factory):
            asset_uri = json.loads(asset_uri)  # done by pctasks base class
            items = streaming.create_item_from_message(asset_uri, storage_factory)
            self.items.extend(items)
            return items

    create_items = MyCreateItems()
    item = pystac.Item(
        "id", {}, None, datetime.datetime(2000, 1, 1), {}, collection="test"
    )
    storage_event["data"]["url"] = json.dumps(item.to_dict())
    storage_event["time"] = "2023-03-27T21:12:27.7409548Z"

    with TempQueue(
        message_decode_policy=None, message_encode_policy=None
    ) as queue_client:
        # put some messages on the queue
        for _ in range(10):
            queue_client.send_message(json.dumps(storage_event))

        task_input = streaming.StreamingCreateItemsInput(
            collection_id="test",
            create_items_function=create_items,
            streaming_options=StreamingTaskOptions(
                queue_url=queue_client.url,
                queue_credential=get_azurite_named_key_credential(),
                visibility_timeout=10,
                message_limit=5,
            ),
        )
        context = TaskContext(run_id="test", storage_factory=StorageFactory())

        task.run(task_input, context)
    assert create_items.items[0].to_dict() == item.to_dict()


def test_streaming_create_items_rewrite_url(monkeypatch, storage_event):
    """
    Test ensuring that the streaming create items task can read from blob storage.

    This also verifies that the URL rewriting from https:// URLs to blob:// works.
    """
    for key, value in {
        AZURITE_STORAGE_ACCOUNT_ENV_VAR: "devstoreaccount1",
        AZURITE_HOST_ENV_VAR: "localhost",
        AZURITE_PORT_ENV_VAR: "10000",
    }.items():
        if key not in os.environ:
            monkeypatch.setenv(key, value)

    host = os.environ[AZURITE_HOST_ENV_VAR]
    port = os.environ[AZURITE_PORT_ENV_VAR]
    setup_azurite()

    with temp_azurite_blob_storage() as root_storage:
        root_storage.write_bytes(
            "data/item.json", json.dumps(BLANK_ITEM.to_dict()).encode()
        )

        url = root_storage.get_url("data/item.json")
        storage_event["data"]["url"] = url
        message_data = StorageEventData.parse_obj(storage_event["data"])

        assert url.startswith(f"http://{host}:{port}")

        task = streaming.StreamingCreateItemsTask()

        def create_items(asset_uri, storage_factory):
            assert asset_uri == root_storage.get_uri("data/item.json")
            result = streaming.create_item_from_item_uri(asset_uri, storage_factory)
            return result

        context = TaskContext(run_id="test", storage_factory=StorageFactory())

        result = task.create_items(
            message_data,
            create_items,
            context.storage_factory,
            collection_id="test-collection",
        )
        expected = BLANK_ITEM.full_copy()
        expected.collection_id = "test-collection"
        assert result[0].to_dict() == expected.to_dict()


def test_streaming_create_items_task_invalid_item(caplog):
    # This implicitly uses
    # - azurite for queues, ...
    task = streaming.StreamingCreateItemsTask()
    bad_item = BLANK_ITEM.clone()
    bad_item.datetime = None  # now invalid
    create_items = lambda *args, **kwargs: [bad_item]

    logger = logging.getLogger("pctasks.task.streaming")
    # logger.setLevel(logging.INFO)
    # handler = logging.StreamHandler()
    # handler.setLevel(logging.INFO)
    logger.addHandler(caplog.handler)

    with TempQueue(
        message_decode_policy=None, message_encode_policy=None
    ) as queue_client:
        # put some messages on the queue
        for _ in range(10):
            queue_client.send_message(
                json.dumps(
                    {
                        "data": {"url": "test.tif"},
                        "time": "2023-03-27T21:12:27.7409548Z",
                    }
                )
            )
        task_input = streaming.StreamingCreateItemsInput(
            collection_id="test",
            create_items_function=create_items,
            streaming_options=StreamingTaskOptions(
                queue_url=queue_client.url,
                queue_credential=get_azurite_named_key_credential(),
                visibility_timeout=1,
                message_limit=5,
            ),
        )
        context = TaskContext(run_id="test", storage_factory=StorageFactory())

        with caplog.at_level(logging.ERROR):
            task.run(task_input, context)

    assert caplog.records


@pytest.mark.usefixtures("temp_cosmosdb_containers")
def test_streaming_create_items_handles_errors(storage_event):
    task = streaming.StreamingCreateItemsTask()
    create_items = BuggyCreateItems()
    storage_event["data"]["url"] = "test.tif"
    storage_event["time"] = "2023-03-27T21:12:27.7409548Z"

    message = azure.storage.queue.QueueMessage(content=json.dumps(storage_event))
    message.id = "test-message"
    message.dequeue_count = 1

    task_input = streaming.StreamingCreateItemsInput(
        collection_id="test",
        create_items_function=create_items,
        streaming_options=StreamingTaskOptions(
            queue_url="http://example.com/",
            queue_credential=get_azurite_named_key_credential(),
            visibility_timeout=10,
            message_limit=5,
        ),
    )

    context = TaskContext(run_id="test", storage_factory=StorageFactory())
    extra_options = task.get_extra_options(task_input, context)
    ok, err = task.process_message(
        message,
        task_input,
        context,
        extra_options=extra_options,
    )

    assert ok is None
    assert err.traceback
    assert err.get_id()
    assert err.run_id == "test"
