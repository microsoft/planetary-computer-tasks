import logging
from pathlib import Path

from pctasks.cli.cli import setup_logging, setup_logging_for_module
from pctasks.dev.test_utils import run_process_items_workflow

HERE = Path(__file__).parent
DATASET_PATH = HERE / "dataset-dev-cluster.yaml"


def test_tabular_ncn():
    run_process_items_workflow(
        DATASET_PATH,
        collection_id="noaa-climate-normals-tabular",
        args={
            "registry": "localhost:5001",
        },
        timeout_seconds=300
    )


if __name__ == "__main__":
    setup_logging(logging.DEBUG)
    setup_logging_for_module("__main__", logging.DEBUG)
    test_tabular_ncn()
    print("Test passed")
    exit(0)
