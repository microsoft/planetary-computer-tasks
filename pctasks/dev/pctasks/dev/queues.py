from typing import Any, Optional
from uuid import uuid1

from azure.storage.queue import QueueClient, QueueServiceClient

from pctasks.core.models.config import QueueConnStrConfig
from pctasks.core.queues import QueueService
from pctasks.dev.constants import get_azurite_connection_string


class TempQueue:
    def __init__(self) -> None:
        suffix = uuid1().hex[:5]
        self.queue_config = QueueConnStrConfig(
            queue_name=f"test-queue-{suffix}",
            connection_string=get_azurite_connection_string(),
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
            try:
                self._service_client.delete_queue(self.queue_config.queue_name)
            except azure.core.exceptions.ResourceNotFoundError:
                pass
            self._service_client.close()
            self._service_client = None
