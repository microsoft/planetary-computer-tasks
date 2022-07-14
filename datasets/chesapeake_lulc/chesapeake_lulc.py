from typing import List, Union

import pystac
from stactools.chesapeake_lulc.stac import create_item

from pctasks.core.models.task import WaitTaskResult
from pctasks.core.storage import StorageFactory
from pctasks.dataset.collection import Collection


class ChesapeakeCollection(Collection):
    @classmethod
    def create_item(
        cls, asset_uri: str, storage_factory: StorageFactory
    ) -> Union[List[pystac.Item], WaitTaskResult]:
        storage, asset_path = storage_factory.get_storage_for_file(asset_uri)
        href = storage.get_url(asset_path)
        item = create_item(href, read_href_modifier=storage.sign)
        return [item]
