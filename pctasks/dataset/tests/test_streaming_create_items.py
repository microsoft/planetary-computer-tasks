import datetime
import json
from pctasks.core.storage import StorageFactory
from pctasks.task.context import TaskContext

import pystac

from pctasks.dataset import streaming
# from pctasks.dev.blob import azurite_queue_client, copy_dir_to_azurite, temp_azurite_blob_storage
from pctasks.dev.queues import TempQueue
from pctasks.dev.constants import AZURITE_ACCOUNT_KEY




def test_streaming_create_items_task():
    task = streaming.StreamingCreateItemsTask()
    count = 0

    def create_items(assert_uri, storage_factory):
        nonlocal count
        count += 1
        if count == 5:
            task.event.set()
        return pystac.Item('id', geometry={}, bbox=None, datetime=datetime.datetime(2000, 1, 1), properties={}) 

    with TempQueue(message_decode_policy=None, message_encode_policy=None) as queue_client:
        # put some messages on the queue
        for _ in range(5):
            queue_client.send_message(
                json.dumps({"data": {"url": "test.tif"}})
            )
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