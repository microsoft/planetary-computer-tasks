from typing import Any, Optional
from uuid import uuid1

import azure.core.exceptions
from azure.storage.queue import QueueClient, QueueServiceClient

from pctasks.core.models.config import QueueConnStrConfig
from pctasks.core.queues import MessageDecodePolicy, MessageEncodePolicy, QueueService
from pctasks.dev.constants import get_azurite_connection_string


class TempQueue:
    def __init__(
        self,
        message_encode_policy: Optional[MessageEncodePolicy] = None,
        message_decode_policy: Optional[MessageDecodePolicy] = None,
        suffix: Optional[str] = None,
        name: Optional[str] = None,
    ) -> None:
        if name and suffix:
            raise ValueError("Specify name or suffix, not both")
        elif not name:
            suffix = suffix or uuid1().hex[:5]
            name = f"test-queue-{suffix}"

        self.message_encode_policy = message_encode_policy
        self.message_decode_policy = message_decode_policy
        self.queue_config = QueueConnStrConfig(
            queue_name=name,
            connection_string=get_azurite_connection_string(),
        )

        self._service_client: Optional[QueueServiceClient] = None
        self._queue_service = QueueService.from_connection_string(
            self.queue_config.connection_string,
            self.queue_config.queue_name,
            message_encode_policy=self.message_encode_policy,
            message_decode_policy=self.message_decode_policy,
        )

    def __enter__(
        self,
    ) -> QueueClient:
        self._service_client = QueueServiceClient.from_connection_string(
            self.queue_config.connection_string,
        )

        try:
            self._service_client.create_queue(self.queue_config.queue_name)
        except azure.core.exceptions.ResourceExistsError:
            pass
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
