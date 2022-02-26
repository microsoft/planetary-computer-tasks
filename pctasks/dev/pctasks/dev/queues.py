from typing import Any, Optional
from uuid import uuid1

from azure.storage.queue import QueueClient, QueueServiceClient

from pctasks.core.queues import QueueService
from pctasks.dev.config import get_queue_config


class TempQueue:
    def __init__(self, permissions: str = "raup") -> None:
        self.queue_config = get_queue_config(
            name=f"testqueue-{uuid1().hex}", permissions=permissions
        )

        self._service_client: Optional[QueueServiceClient] = None
        self._queue_service = QueueService.from_connection_string(
            self.queue_config.connection_string,
            self.queue_config.queue_name,
        )

    def __enter__(self) -> QueueClient:
        self._service_client = QueueServiceClient.from_connection_string(
            self.queue_config.connection_string
        )

        self._service_client.create_queue(self.queue_config.queue_name)

        return self._queue_service.__enter__()

    def __exit__(self, *args: Any) -> None:
        self._queue_service.__exit__(*args)
        if self._service_client:
            self._service_client.delete_queue(self.queue_config.queue_name)
            self._service_client.close()
            self._service_client = None
