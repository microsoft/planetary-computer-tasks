import logging
from pathlib import Path

from pctasks.cli.cli import setup_logging, setup_logging_for_module
from pctasks.dev.test_utils import run_process_items_workflow

HERE = Path(__file__).parent
DATASET_PATH = HERE / ".." / "dataset-dev-cluster.yaml"


def test_1h_pass1():
    run_process_items_workflow(
        DATASET_PATH,
        "noaa-mrms-qpe-1h-pass1",
        args={
            "registry": "localhost:5001",
        },
    )


def test_1h_pass2():
    run_process_items_workflow(
        DATASET_PATH,
        "noaa-mrms-qpe-1h-pass2",
        args={
            "registry": "localhost:5001",
        },
    )


def test_24h_2pass():
    run_process_items_workflow(
        DATASET_PATH,
        "noaa-mrms-qpe-24h-pass2",
        args={
            "registry": "localhost:5001",
        },
    )


if __name__ == "__main__":
    setup_logging(logging.DEBUG)
    setup_logging_for_module("__main__", logging.DEBUG)
    test_1h_pass1()
    test_1h_pass2()
    test_24h_2pass()
    print("All tests passed")
    exit(0)
