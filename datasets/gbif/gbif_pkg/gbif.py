from typing import List, Union

import pystac

from pctasks.core.models.task import WaitTaskResult
from pctasks.core.storage import StorageFactory
from pctasks.core.storage.blob import BlobStorage
from pctasks.dataset.collection import Collection


class GBIFCollection(Collection):  # type: ignore
    @classmethod
    def create_item(
        cls, asset_uri: str, storage_factory: StorageFactory
    ) -> Union[List[pystac.Item], WaitTaskResult]:
        from gbif_pkg.gbif_tools import create_item

        storage, path = storage_factory.get_storage_for_file(asset_uri)
        if isinstance(storage, BlobStorage):
            az_uri = f"az://{storage.container_name}/{path}".rstrip("/")
            https_href = f"https://{storage.storage_account_name}.blob.core.windows.net/{storage.container_name}/{path}".rstrip("/")
            storage_options = dict(account_name=storage.storage_account_name)
            asset_extra_fields = {
                "table:storage_options": storage_options,
                "msft:partition_info": {
                    "is_partitioned": True
                }
            }
            item = create_item(
                az_uri,
                storage_options=storage_options,
                asset_extra_fields=asset_extra_fields,
                asset_href_override=https_href,
            )
        else:
            href = storage.get_url(path).rstrip("/")
            item = create_item(
                href, storage_options=dict(), asset_extra_fields=None
            )

        return [item]
