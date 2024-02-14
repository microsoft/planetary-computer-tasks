import logging
from pathlib import Path

import io_lulc
from pctasks.cli.cli import setup_logging, setup_logging_for_module
from pctasks.core.storage import StorageFactory
from pctasks.dev.test_utils import run_process_items_workflow

HERE = Path(__file__).parent
DATASET_PATH = HERE / ".." / "dataset.yaml"


def test_10_class() -> None:
    run_process_items_workflow(
        DATASET_PATH,
        "io-lulc",
        args={
            "registry": "localhost:5001",
        },
    )


def test_9_class() -> None:
    run_process_items_workflow(
        DATASET_PATH,
        "io-lulc-9-class",
        args={
            "registry": "localhost:5001",
        },
    )


def test_2023() -> None:
    asset_uri = (
        "blob://ai4edataeuwest/io-lulc/io-annual-lulc-v02/01C_20170101-20180101.tif"
    )
    storage_factory = StorageFactory()
    [item] = io_lulc.NineClassV2IOCollection.create_item(asset_uri, storage_factory)

    assert item is not None


if __name__ == "__main__":
    setup_logging(logging.DEBUG)
    setup_logging_for_module("__main__", logging.DEBUG)
    test_10_class()
    test_9_class()
    print("All tests passed")
    exit(0)
