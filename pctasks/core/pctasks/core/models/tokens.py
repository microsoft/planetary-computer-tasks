from typing import Dict, Optional

from pctasks.core.models.base import PCBaseModel


class ContainerTokens(PCBaseModel):
    token: Optional[str] = None
    blobs: Optional[Dict[str, str]] = None


class StorageAccountTokens(PCBaseModel):
    token: Optional[str] = None
    containers: Optional[Dict[str, ContainerTokens]] = None
