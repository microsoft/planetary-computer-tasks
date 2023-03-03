import datetime
import json
from typing import List

import pystac

from pctasks.core.storage import StorageFactory
from pctasks.dataset import streaming
from pctasks.dev.constants import AZURITE_ACCOUNT_KEY
from pctasks.dev.queues import TempQueue
from pctasks.task.context import TaskContext


def test_streaming_create_items_task():
    task = streaming.StreamingCreateItemsTask()
    count = 0

    def create_items(
        assert_uri: str, storage_factory: StorageFactory
    ) -> List[pystac.Item]:
        nonlocal count
        count += 1
        if count == 5:
            task.event.set()
        result = pystac.Item(
            "id",
            geometry={},
            bbox=None,
            datetime=datetime.datetime(2000, 1, 1),
            properties={},
        )
        return [result]

    with TempQueue(
        message_decode_policy=None, message_encode_policy=None
    ) as queue_client:
        # put some messages on the queue
        for _ in range(5):
            queue_client.send_message(json.dumps({"data": {"url": "test.tif"}}))
        task_input = streaming.StreamingCreateItemsInput(
            collection_id="test",
            create_items_function=create_items,
            queue_url=queue_client.url,
            queue_credential=AZURITE_ACCOUNT_KEY,
            visibility_timeout=10,
        )
        context = TaskContext(run_id="test", storage_factory=StorageFactory())

        task.run(task_input, context)
    assert count == 5

    ...
