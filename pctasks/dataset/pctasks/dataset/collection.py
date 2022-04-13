from abc import ABC, abstractmethod
from typing import List, Union

import pystac

from pctasks.core.models.task import WaitTaskResult
from pctasks.core.storage import StorageFactory
from pctasks.dataset.items.task import CreateItemsTask
from pctasks.task import Task


class Collection(ABC):
    @classmethod
    @abstractmethod
    def create_item(
        cls, asset_uri: str, storage_factory: StorageFactory
    ) -> Union[List[pystac.Item], WaitTaskResult]:
        pass

    @classmethod
    def create_items_task(cls) -> Task:
        return CreateItemsTask(cls.create_item)
