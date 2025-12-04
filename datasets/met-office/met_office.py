from typing import Union

from pctasks.core.models.task import WaitTaskResult
from pctasks.core.storage import StorageFactory
from pctasks.dataset.collection import Collection
from pystac import Item
from stactools.met_office_deterministic import stac


class MetOfficeCollection(Collection):
    @classmethod
    def create_item(
        cls, asset_uri: str, storage_factory: StorageFactory
    ) -> Union[list[Item], WaitTaskResult]:
        storage = storage_factory.get_storage(asset_uri)
        hrefs = list(storage.get_url(path) for path in storage.list_files())
        items = stac.create_items(hrefs)
        return items
