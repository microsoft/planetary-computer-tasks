import os
from typing import Optional, Tuple

from cachetools import Cache, LRUCache, cachedmethod

from pctasks.core.storage import blob, local
from pctasks.core.storage.base import Storage
from pctasks.core.tokens import Tokens


def get_storage(
    uri: str,
    sas_token: Optional[str] = None,
    account_key: Optional[str] = None,
    tokens: Optional[Tokens] = None,
    account_url: Optional[str] = None,
) -> Storage:
    """Gets storage that represents the folder at the uri."""
    if blob.BlobUri.matches(uri):
        blob_uri = blob.BlobUri(uri)
        token: Optional[str] = sas_token
        if account_key:
            return blob.BlobStorage.from_account_key(
                blob_uri,
                account_key=account_key,
                account_url=account_url,
            )

        # Use sas tokens or default credentials
        if not token and tokens:
            token = tokens.get_token_from_uri(blob_uri)
        return blob.BlobStorage.from_uri(
            blob_uri=blob_uri, sas_token=token, account_url=account_url
        )

    else:
        return local.LocalStorage(uri)


def get_storage_for_file(
    file_uri: str,
    sas_token: Optional[str] = None,
    account_key: Optional[str] = None,
    tokens: Optional[Tokens] = None,
    account_url: Optional[str] = None,
) -> Tuple[Storage, str]:
    """Returns storage and the path to the file based on that storage."""
    if blob.BlobUri.matches(file_uri):
        blob_uri = blob.BlobUri(file_uri)
        storage = get_storage(
            str(blob_uri.base_uri),
            sas_token=sas_token,
            account_key=account_key,
            tokens=tokens,
            account_url=account_url,
        )
        path = blob_uri.blob_name or ""
        return (storage, path)
    else:
        parent = os.path.dirname(file_uri)
        path = os.path.basename(file_uri)
        return (get_storage(parent), path)


def read_text(
    file_uri: str,
    sas_token: Optional[str] = None,
    account_key: Optional[str] = None,
    tokens: Optional[Tokens] = None,
    account_url: Optional[str] = None,
) -> str:
    storage, path = get_storage_for_file(
        file_uri,
        sas_token=sas_token,
        account_key=account_key,
        tokens=tokens,
        account_url=account_url,
    )
    return storage.read_text(path)


class StorageFactory:
    """Factory that produces Storage objects.

    Fetches cached storage objects for folder and file URIs.
    Uses Tokens to enable SAS token IO from blob storage.
    """

    tokens: Optional[Tokens]
    """Optional tokens to use for blob storage."""

    account_url: Optional[str]
    """Blob storage endpoint. Useful for testing against Azurite."""

    _cache: Cache

    def __init__(
        self, tokens: Optional[Tokens] = None, account_url: Optional[str] = None
    ) -> None:
        self._cache = LRUCache(maxsize=100)
        self.tokens = tokens
        self.account_url = account_url

    def __repr__(self):
        return f"<StorageFactory(account_url={self.account_url}) with {len(self._cache)} tokens>"

    @cachedmethod(lambda self: self._cache)
    def get_storage(self, uri: str) -> Storage:
        """Gets storage that represents the folder at the uri."""
        if uri in self._cache:
            return self._cache[uri]
        storage = get_storage(uri, tokens=self.tokens, account_url=self.account_url)
        self._cache[uri] = storage
        return storage

    def get_storage_for_file(self, file_uri: str) -> Tuple[Storage, str]:
        """Returns storage and the path to the file based on that storage."""
        if blob.BlobUri.matches(file_uri):
            blob_uri = blob.BlobUri(file_uri)
            storage = self.get_storage(str(blob_uri.base_uri))
            path = blob_uri.blob_name or ""
            return (storage, path)
        else:
            parent = os.path.dirname(file_uri)
            path = os.path.basename(file_uri)
            return (self.get_storage(parent), path)

    def clear_cache(self) -> None:
        """Clears the cache."""
        self._cache.clear()


__all__ = ["Storage", "StorageFactory", "read_text"]
