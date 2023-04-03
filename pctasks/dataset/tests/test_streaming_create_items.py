import datetime
import json

import pystac

from pctasks.core.storage import StorageFactory
from pctasks.dataset import streaming
from pctasks.dev.constants import AZURITE_ACCOUNT_KEY
from pctasks.dev.queues import TempQueue
from pctasks.task.context import TaskContext
from pctasks.task.streaming import StreamingTaskOptions


class CreateItems:
    def __init__(self):
        self.count = 0

    def __call__(self, asset_uri, storage_factory):
        self.count += 1
        result = pystac.Item(
            "id",
            geometry={},
            bbox=None,
            datetime=datetime.datetime(2000, 1, 1),
            properties={},
        )
        return [result]


def test_streaming_create_items_task():
    # This implicitly uses
    # - azurite for queues, ...
    task = streaming.StreamingCreateItemsTask()
    create_items = CreateItems()

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
                queue_credential=AZURITE_ACCOUNT_KEY,
                visibility_timeout=10,
                message_limit=5,
            ),
        )
        context = TaskContext(run_id="test", storage_factory=StorageFactory())

        task.run(task_input, context)
    # I'm confused why this isn't 5. It seems like we're fetching a batch of
    # messages from the queue at once.
    assert create_items.count == 10


def test_streaming_create_items_from_message():
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

    with TempQueue(
        message_decode_policy=None, message_encode_policy=None
    ) as queue_client:
        # put some messages on the queue
        for _ in range(10):
            queue_client.send_message(
                json.dumps(
                    {
                        "data": {"url": json.dumps(item.to_dict())},
                        "time": "2023-03-27T21:12:27.7409548Z",
                    }
                )
            )

        task_input = streaming.StreamingCreateItemsInput(
            collection_id="test",
            create_items_function=create_items,
            streaming_options=StreamingTaskOptions(
                queue_url=queue_client.url,
                queue_credential=AZURITE_ACCOUNT_KEY,
                visibility_timeout=10,
                message_limit=5,
            ),
        )
        context = TaskContext(run_id="test", storage_factory=StorageFactory())

        task.run(task_input, context)
    assert create_items.items[0].to_dict() == item.to_dict()
