import datetime
from pctasks.core.storage import StorageFactory
from pctasks.task.context import TaskContext

import pystac

from pctasks.dataset import streaming
from pctasks.dev.blob import azurite_queue_client, copy_dir_to_azurite, temp_azurite_blob_storage




def test_streaming_create_items_task():
    task = streaming.StreamingCreateItemsTask()
    count = 0

    def create_items(assert_uri, storage_factory):
        print("hey!")
        nonlocal count
        count += 1
        if count == 5:
            task.event.set()
        return pystac.Item('id', geometry={}, bbox=None, datetime=datetime.datetime(2000), properties={}) 

    with temp_azurite_blob_storage():
        # put some messages on the queue
        queue_client = azurite_queue_client()
        task_input = streaming.StreamingCreateItemsInput(
            collection_id="test",
            create_items_function=create_items,
            queue_url=queue_client.url,
            visibility_timeout=10,
        )
        context = TaskContext(run_id="test", storage_factory=StorageFactory())

        task.run(task_input, context)

    ...