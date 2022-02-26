from naip.dataset import Naip

from pctasks.core.storage import StorageFactory


def test_create_item():
    collection = Naip()

    collection.create_item("test", StorageFactory())
