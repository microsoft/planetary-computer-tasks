from pathlib import Path

import pytest

from pctasks.dev.test_utils import run_process_items_workflow

HERE = Path(__file__).parent
DATASET_PATH = HERE / "dataset-dev-cluster.yaml"


@pytest.mark.parametrize(
    "collection",
    ["noaa-mrms-qpe-1h-pass1", "noaa-mrms-qpe-1h-pass2", "noaa-mrms-qpe-24h-pass2"],
)
def test_collection(collection):
    run_process_items_workflow(
        DATASET_PATH,
        collection,
        args={
            "registry": "localhost:5001",
        },
        splits_limit=1,
        chunks_limit=2,
        timeout_seconds=600,
    )
