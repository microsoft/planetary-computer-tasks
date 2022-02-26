from abc import ABC, abstractmethod
from typing import List, Union

import pystac

from pctasks.core.models.task import WaitTaskResult
from pctasks.core.storage import StorageFactory
from pctasks.dataset.chunks.task import CreateChunksTask
from pctasks.dataset.items.task import CreateItemsTask
from pctasks.task import Task


class Collection(ABC):
    @abstractmethod
    def create_item(
        self, asset_uri: str, storage_factory: StorageFactory
    ) -> Union[List[pystac.Item], WaitTaskResult]:
        pass

    @property
    def create_chunks_task(self) -> Task:
        return CreateChunksTask()

    @property
    def create_items_task(self) -> Task:
        return CreateItemsTask(self.create_item)
