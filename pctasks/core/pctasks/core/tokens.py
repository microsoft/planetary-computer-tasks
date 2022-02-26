from typing import Dict, Optional, Union

from pctasks.core.models.tokens import StorageAccountTokens
from pctasks.core.storage.blob import BlobUri


class Tokens:
    def __init__(self, tokens: Optional[Dict[str, StorageAccountTokens]]) -> None:
        self._tokens = tokens

    def get_token(
        self,
        storage_account: str,
        container: Optional[str],
        blob: Optional[str],
    ) -> Optional[str]:
        if not self._tokens:
            return None

        account_tokens = self._tokens.get(storage_account)
        if not account_tokens:
            return None
        else:
            account_match: Optional[str] = None
            container_match: Optional[str] = None

            account_match = account_tokens.token
            if container and account_tokens.containers:
                container_tokens = account_tokens.containers.get(container)
                if container_tokens:
                    container_match = container_tokens.token
                    if (
                        blob
                        and container_tokens.blobs
                        and blob in container_tokens.blobs
                    ):
                        return container_tokens.blobs.get(blob)
            return container_match or account_match

    def get_token_from_uri(self, uri: Union[str, BlobUri]) -> Optional[str]:
        if isinstance(uri, str):
            if not BlobUri.matches(uri):
                return None
            uri = BlobUri(uri)
        return self.get_token(
            uri.storage_account_name, uri.container_name, uri.blob_name
        )

    def get_models(self) -> Dict[str, StorageAccountTokens]:
        return self._tokens or {}
