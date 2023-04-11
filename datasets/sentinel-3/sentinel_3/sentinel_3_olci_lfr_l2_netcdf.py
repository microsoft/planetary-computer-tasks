from typing import List, Union

import pystac

import pctasks.dataset.collection
from pctasks.core.models.task import WaitTaskResult
from pctasks.core.storage import StorageFactory


class Collection(pctasks.dataset.collection.Collection):
    @classmethod
    def create_item(
        cls, asset_uri: str, storage_factory: StorageFactory
    ) -> Union[List[pystac.Item], WaitTaskResult]:
        pass
 