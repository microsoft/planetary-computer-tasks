import datetime
import json
from typing import List

import pystac

from pctasks.core.storage import StorageFactory
from pctasks.dataset import streaming
from pctasks.dev.constants import AZURITE_ACCOUNT_KEY
from pctasks.dev.queues import TempQueue
from pctasks.task.context import TaskContext


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
    task = streaming.StreamingCreateItemsTask()
    create_items = CreateItems()

    with TempQueue(
        message_decode_policy=None, message_encode_policy=None
    ) as queue_client:
        # put some messages on the queue
        for _ in range(10):
            queue_client.send_message(json.dumps({"data": {"url": "test.tif"}}))
        task_input = streaming.StreamingCreateItemsInput(
            collection_id="test",
            create_items_function=create_items,
            queue_url=queue_client.url,
            queue_credential=AZURITE_ACCOUNT_KEY,
            visibility_timeout=10,
            message_limit=5,
        )
        context = TaskContext(run_id="test", storage_factory=StorageFactory())

        task.run(task_input, context)
    # I'm confused why this isn't 5. It seems like we're fetching a batch of
    # messages from the queue at once.
    assert create_items.count == 10
