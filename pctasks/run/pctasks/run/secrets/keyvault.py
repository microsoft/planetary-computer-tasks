import threading
from typing import Any, Optional, Union

from azure.identity import ClientSecretCredential, DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from cachetools import Cache, LRUCache, TTLCache, cachedmethod

from pctasks.core.utils.backoff import with_backoff
from pctasks.run.secrets.base import SecretsProvider
from pctasks.run.settings import RunSettings
from pctasks.core.utils.credential import get_credential

secret_lock = threading.Lock()


class KeyvaultSecretsProvider(SecretsProvider):
    _cache: Cache = LRUCache(maxsize=100)

    _creds: Union[DefaultAzureCredential, ClientSecretCredential]

    def __init__(self, settings: Optional[RunSettings]) -> None:
        if not settings:
            raise ValueError("Must be initialized with a settings object")
        super().__init__(settings)

        if not settings.keyvault_url:
            # Should be handled by model validation
            raise ValueError("Keyvault url not set")
        self.keyvault_url = settings.keyvault_url
        tenant_id = settings.keyvault_sp_tenant_id or None
        client_id = settings.keyvault_sp_client_id or None
        client_secret = settings.keyvault_sp_client_secret or None

        self._client: Optional[SecretClient] = None
        self._cache: Cache = TTLCache(maxsize=128, ttl=60)

        if tenant_id and client_id and client_secret:
            self._creds = ClientSecretCredential(tenant_id, client_id, client_secret)
        else:
            self._creds = get_credential()

    def __enter__(self) -> "SecretsProvider":
        self._client = SecretClient(
            vault_url=self.keyvault_url,
            credential=self._creds,
        )
        return self

    def __exit__(self, *args: Any) -> None:
        if self._client:
            self._client.close()

    @cachedmethod(lambda self: self._cache)
    def _fetch_secret(self, name: str) -> str:
        return with_backoff(
            lambda: self._client.get_secret(name).value  # type:ignore
        )

    def get_secret(self, name: str) -> str:
        if not self._client:
            raise ValueError("Must be used as a context manager")

        with secret_lock:
            return self._fetch_secret(name)

    @classmethod
    @cachedmethod(lambda cls: cls._cache, key=lambda _, settings: settings.keyvault_url)
    def get_provider(
        cls,
        settings: RunSettings,
    ) -> "KeyvaultSecretsProvider":
        return cls(settings)
