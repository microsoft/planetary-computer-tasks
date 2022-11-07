from abc import ABC, abstractmethod
from typing import List, Union

import pystac

from pctasks.core.models.task import WaitTaskResult
from pctasks.core.storage import StorageFactory
from pctasks.dataset.chunks.task import CreateChunksTask
from pctasks.dataset.items.task import CreateItemsTask
from pctasks.dataset.splits.task import CreateSplitsTask
from pctasks.task.task import Task


class Collection(ABC):
    """Base class for defining how Items in a Collection are created.

    To create a Collection, subclass this class and implement the create_item
    method. You may also override the other methods, which define the tasks
    that create splits, create chunks, and creates items from the chunk files.
    However the defaults for those tasks should generally work, and you should
    normally only need to supply the create_item method.

    If you're working with a stactools package, this class can be as simple
    as calling out to the stactools package to create an Item from
    an asset.

    Example:

        class MyCollection(Collection):
            def create_item(
                self, asset_uri: str, storage_factory: StorageFactory
            ) -> Union[List[pystac.Item], WaitTaskResult]:
                storage, asset_path = storage_factor.get_storage_for_file(asset_uri)
                signed_url = storage.get_authenticated_url(asset_path)
                item = stactools.mypackage.create_item(signed_url)
                return [item]

    """

    @classmethod
    @abstractmethod
    def create_item(
        cls, asset_uri: str, storage_factory: StorageFactory
    ) -> Union[List[pystac.Item], WaitTaskResult]:
        """Create an Item from the given asset_uri.

        Returns a list of Items if the asset is a collection, or a WaitTaskResult
        when there is a reason to delay the processing of that item (for example,
        when not all auxiliary files are available).
        """
        pass

    @classmethod
    def create_items_task(cls) -> Task:
        return CreateItemsTask(cls.create_item, cls.deduplicate_items)

    @classmethod
    def create_splits_task(cls) -> Task:
        return CreateSplitsTask()

    @classmethod
    def create_chunks_task(cls) -> Task:
        return CreateChunksTask()

    @classmethod
    def deduplicate_items(cls, items: List[pystac.Item]) -> List[pystac.Item]:
        """
        Deduplicate items in a chunkset.

        This will be called by :meth:`CreateItemsTask.run` as part of processing a chunkset,
        to ensure that chunksets provided to pgstac for ingest are valid (it requires no
        duplicate item IDs in a chunkset).
        
        By default, a ``ValueError`` is raised if there are any duplicates in a chunkset.
        Subclasses are free to override this method to use dataset-specific logic to
        pick the "right" item.
        """
        if len(items) != len(set(x.id for x in items)):
            raise ValueError("Duplicate IDs detected in chunkset")
        return items


class PremadeItemCollection(Collection):
    @classmethod
    def create_item(
        cls, asset_uri: str, storage_factory: StorageFactory
    ) -> Union[List[pystac.Item], WaitTaskResult]:
        """
        Create items from URLs to GeoJSON files.

        Use this :ref:`Collection` subclass when your STAC items already exist
        as JSON files in some storage location. This reads the file and returns
        the Item parsed from that file.
        """
        asset_storage, path = storage_factory.get_storage_for_file(asset_uri)
        item_href = asset_storage.get_authenticated_url(path)
        return [pystac.Item.from_file(item_href)]
