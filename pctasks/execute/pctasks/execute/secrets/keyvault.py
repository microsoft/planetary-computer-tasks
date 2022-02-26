from functools import lru_cache
from typing import Any, Optional

from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from cachetools import Cache, TTLCache, cachedmethod

from pctasks.core.utils.backoff import with_backoff
from pctasks.execute.secrets.base import SecretsProvider


class KeyvaultSecretsProvider(SecretsProvider):
    def __init__(self, keyvault_url: str) -> None:
        self.keyvault_url = keyvault_url
        self._client: Optional[SecretClient] = None
        self._cache: Cache = TTLCache(maxsize=128, ttl=60)

    def __enter__(self) -> "SecretsProvider":
        self._client = SecretClient(
            vault_url=self.keyvault_url,
            credential=DefaultAzureCredential(),
        )
        return self

    def __exit__(self, *args: Any) -> None:
        if self._client:
            self._client.close()

    @cachedmethod(lambda self: self._cache)
    def get_secret(self, name: str) -> str:
        if not self._client:
            raise ValueError("Must be used as a context manager")

        return with_backoff(
            lambda: self._client.get_secret(name).value  # type:ignore
        )

    @classmethod
    @lru_cache(maxsize=10)
    def get_provider(cls, keyvault_url: str) -> "KeyvaultSecretsProvider":
        return cls(keyvault_url)
