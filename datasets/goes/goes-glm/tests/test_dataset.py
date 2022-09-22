import logging
from pathlib import Path

from pctasks.cli.cli import setup_logging, setup_logging_for_module
from pctasks.dev.test_utils import run_process_items_workflow

HERE = Path(__file__).parent
DATASET_PATH = HERE / ".." / "dataset-dev-cluster.yaml"


def test_goes_glm():
    run_process_items_workflow(
        DATASET_PATH,
        collection_id="goes-glm",
        args={
            "registry": "localhost:5001",
        },
        splits_limit=1,
        chunks_limit=2
    )


if __name__ == "__main__":
    setup_logging(logging.DEBUG)
    setup_logging_for_module("__main__", logging.DEBUG)
    test_goes_glm()
    print("Test passed")
    exit(0)
