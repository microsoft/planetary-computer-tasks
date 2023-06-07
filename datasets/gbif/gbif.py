from typing import Dict, List, Optional, Union

import pystac
from stactools.gbif import stac

from pctasks.core.models.task import WaitTaskResult
from pctasks.core.storage import StorageFactory
from pctasks.core.storage.blob import BlobStorage
from pctasks.dataset.collection import Collection


class GBIFCollection(Collection):  # type: ignore
    @classmethod
    def create_item(
        cls, asset_uri: str, storage_factory: StorageFactory
    ) -> Union[List[pystac.Item], WaitTaskResult]:

        storage_options: Optional[Dict[str, str]]
        asset_extra_fields: Optional[Dict[str, Optional[Dict[str, str]]]]

        storage, path = storage_factory.get_storage_for_file(asset_uri)

        if isinstance(storage, BlobStorage):
            # we want the az url.
            href = f"az://{storage.container_name}/{path}"
            storage_options = dict(account_name=storage.storage_account_name)
            asset_extra_fields = {"table:storage_options": storage_options}
        else:
            href = storage.get_url(path)
            storage_options = dict()
            asset_extra_fields = None

        href = href.rstrip("/")

        item = stac.create_item(
            href, storage_options=storage_options, asset_extra_fields=asset_extra_fields
        )

        return [item]
