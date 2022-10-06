from pathlib import Path

import pytest

from pctasks.dev.test_utils import run_process_items_workflow

HERE = Path(__file__).parent
DATASET_PATH = HERE / ".." / "dataset.yaml"


# NOTE: Use pytest
# NOTE: Change the COG_CONTAINER variable in noaa_nclimgrid.py to
# "blob://devstoreaccount1/nclimgrid-cogs" to avoid saving COGs to the remote
# Azure container


def test_daily_prelim():
    run_process_items_workflow(
        DATASET_PATH,
        collection_id="noaa-nclimgrid-daily-prelim",
        args={
            "registry": "localhost:5001",
        },
        chunks_limit=1,
        timeout_seconds=1000,
    )


def test_daily_scaled():
    run_process_items_workflow(
        DATASET_PATH,
        collection_id="noaa-nclimgrid-daily-scaled",
        args={
            "registry": "localhost:5001",
        },
        chunks_limit=1,
        timeout_seconds=1000,
    )


# The monthly data exists in a single set of NetCDFs, so only a single asset
# (line) in a single asset chunkfile is generated --> all Items and COGs for the
# monthly collection are created from a single asset uri. This is onerous for
# testing, so best not to run it. The monthly dataset was ingested into PC Test,
# which more or less serves as a proxy for this test.
@pytest.mark.slow
def test_monthly():
    run_process_items_workflow(
        DATASET_PATH,
        collection_id="noaa-nclimgrid-monthly",
        args={
            "registry": "localhost:5001",
        },
        chunks_limit=1,
        timeout_seconds=10000,
    )
