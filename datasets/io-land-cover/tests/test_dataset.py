import logging
from pathlib import Path

from pctasks.cli.cli import setup_logging, setup_logging_for_module
from pctasks.dev.test_utils import run_process_items_workflow

HERE = Path(__file__).parent
DATASET_PATH = HERE / ".." / "dataset.yaml"


def test_10_class():
    run_process_items_workflow(
        DATASET_PATH,
        "io-lulc",
        args={
            "registry": "localhost:5001",
        },
    )


def test_9_class():
    run_process_items_workflow(
        DATASET_PATH,
        "io-lulc-9-class",
        args={
            "registry": "localhost:5001",
        },
    )


if __name__ == "__main__":
    setup_logging(logging.DEBUG)
    setup_logging_for_module("__main__", logging.DEBUG)
    test_10_class()
    test_9_class()
    print("All tests passed")
    exit(0)
