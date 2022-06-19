import threading
from functools import lru_cache
from typing import Any, Optional, Union

from azure.identity import ClientSecretCredential, DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from cachetools import Cache, TTLCache, cachedmethod

from pctasks.core.utils.backoff import with_backoff
from pctasks.run.secrets.base import SecretsProvider

secret_lock = threading.Lock()


class KeyvaultSecretsProvider(SecretsProvider):
    _creds: Union[DefaultAzureCredential, ClientSecretCredential]

    def __init__(
        self,
        keyvault_url: str,
        tenant_id: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
    ) -> None:
        self.keyvault_url = keyvault_url
        self._client: Optional[SecretClient] = None
        self._cache: Cache = TTLCache(maxsize=128, ttl=60)

        if tenant_id and client_id and client_secret:
            self._creds = ClientSecretCredential(tenant_id, client_id, client_secret)
        else:
            self._creds = DefaultAzureCredential()

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
    @lru_cache(maxsize=10)
    def get_provider(
        cls,
        keyvault_url: str,
        tenant_id: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
    ) -> "KeyvaultSecretsProvider":
        return cls(keyvault_url, tenant_id, client_id, client_secret)
