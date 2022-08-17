import logging
from pathlib import Path

from pctasks.cli.cli import setup_logging, setup_logging_for_module
from pctasks.dev.test_utils import run_process_items_workflow

HERE = Path(__file__).parent
DATASET_PATH = HERE / ".." / "dataset.yaml"


def test_lc7():
    run_process_items_workflow(
        DATASET_PATH,
        "chesapeake-lc-7",
        args={
            "registry": "localhost:5001",
        },
    )


def test_lc13():
    run_process_items_workflow(
        DATASET_PATH,
        "chesapeake-lc-13",
        args={
            "registry": "localhost:5001",
        },
    )


def test_lu():
    run_process_items_workflow(
        DATASET_PATH,
        "chesapeake-lu",
        args={
            "registry": "localhost:5001",
        },
    )


if __name__ == "__main__":
    setup_logging(logging.DEBUG)
    setup_logging_for_module("__main__", logging.DEBUG)
    test_lc7()
    test_lc13()
    test_lu()
    print("All tests passed")
    exit(0)
