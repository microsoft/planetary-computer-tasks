import pctasks.core.models.task


def get_streaming_task_definition():
    """A task definition for a streaming workflow."""
    image = "localhost:5001/pctasks-task-base:latest"
    cosmos = "https://pclowlatencytesttom.documents.azure.com:443/"
    function = "pctasks.dataset.streaming.create_item_from_item_uri"
    return pctasks.core.models.task.TaskDefinition(
        **{
            "id": "create-items",
            "image": image,
            "task": "pctasks.dataset.streaming:StreamingCreateItemsTask",
            "args": {
                "streaming_options": {
                    "queue_url": "http://127.0.0.1:10001/devstoreaccount1/test",
                    "visibility_timeout": 30,
                    "min_replica_count": 0,
                    "max_replica_count": 10,
                    "polling_interval": 30,
                    "trigger_queue_length": 100,
                },
                "container_name": "items",
                "options": {"skip_validation": False},
                "cosmos_endpoint": cosmos,
                "db_name": "lowlatencydb",
                "create_items_function": function,
                "collection_id": "test",
            },
            "schema_version": "1.0.0",
        }
    )
