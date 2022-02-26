from typing import Any, Callable, Optional, Tuple, Union

from azure.storage.queue import (
    BinaryBase64DecodePolicy,
    BinaryBase64EncodePolicy,
    QueueClient,
    QueueServiceClient,
)

from pctasks.core.models.config import QueueConnStrConfig, QueueSasConfig


class QueueError(Exception):
    pass


class QueueService:
    def __init__(
        self,
        get_clients: Callable[[], Tuple[Optional[QueueServiceClient], QueueClient]],
    ) -> None:
        self._get_clients = get_clients
        self._service_client: Optional[QueueServiceClient] = None
        self._queue_client: Optional[QueueClient] = None

    def _ensure_queue_client(self) -> None:
        if not self._queue_client:
            raise QueueError("Table client not initialized. Use as a context manager.")

    def __enter__(self) -> QueueClient:
        self._service_client, self._queue_client = self._get_clients()
        return self._queue_client

    def __exit__(self, *args: Any) -> None:
        if self._queue_client:
            self._queue_client.close()
            self._queue_client = None
        if self._service_client:
            self._service_client.close()
            self._service_client = None

    @classmethod
    def from_sas_token(
        cls,
        account_url: str,
        sas_token: str,
        queue_name: str,
    ) -> "QueueService":
        def _get_clients(
            _url: str = account_url, _token: str = sas_token, _queue: str = queue_name
        ) -> Tuple[Optional[QueueServiceClient], QueueClient]:
            service_client = QueueServiceClient(
                account_url=_url,
                credential=_token,
            )
            return (
                service_client,
                service_client.get_queue_client(
                    queue=_queue,
                    message_encode_policy=BinaryBase64EncodePolicy(),
                    message_decode_policy=BinaryBase64DecodePolicy(),
                ),
            )

        return cls(_get_clients)

    @classmethod
    def from_connection_string(
        cls, connection_string: str, queue_name: str
    ) -> "QueueService":
        def _get_clients(
            _conn_str: str = connection_string, _queue: str = queue_name
        ) -> Tuple[Optional[QueueServiceClient], QueueClient]:
            service_client = QueueServiceClient.from_connection_string(
                conn_str=_conn_str
            )
            return (
                service_client,
                service_client.get_queue_client(
                    queue=_queue,
                    message_encode_policy=BinaryBase64EncodePolicy(),
                    message_decode_policy=BinaryBase64DecodePolicy(),
                ),
            )

        return cls(_get_clients)

    @classmethod
    def from_account_key(
        cls,
        account_url: str,
        account_key: str,
        queue_name: str,
    ) -> "QueueService":
        def _get_clients(
            _key: str = account_key,
            _url: str = account_url,
            _queue: str = queue_name,
        ) -> Tuple[Optional[QueueServiceClient], QueueClient]:
            service_client = QueueServiceClient(account_url=_url, credential=_key)
            return (
                service_client,
                service_client.get_queue_client(
                    queue=_queue,
                    message_encode_policy=BinaryBase64EncodePolicy(),
                    message_decode_policy=BinaryBase64DecodePolicy(),
                ),
            )

        return cls(_get_clients)

    @classmethod
    def from_config(
        cls, config: Union[QueueSasConfig, QueueConnStrConfig]
    ) -> "QueueService":
        if isinstance(config, QueueSasConfig):
            return cls.from_sas_token(
                account_url=config.account_url,
                sas_token=config.sas_token,
                queue_name=config.queue_name,
            )
        else:
            return cls.from_connection_string(
                config.connection_string, config.queue_name
            )
