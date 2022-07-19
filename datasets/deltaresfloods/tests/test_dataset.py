import logging
from pathlib import Path

from pctasks.cli.cli import setup_logging, setup_logging_for_module
from pctasks.dev.test_utils import run_process_items_workflow

HERE = Path(__file__).parent
DATASET_PATH = HERE / ".." / "dataset.yaml"


def test_dataset():
    run_process_items_workflow(
        DATASET_PATH, image="localhost:5001/pctasks-task-base:latest"
    )


if __name__ == "__main__":
    setup_logging(logging.DEBUG)
    setup_logging_for_module("__main__", logging.DEBUG)
    test_dataset()
    print("All tests passed")
    exit(0)
