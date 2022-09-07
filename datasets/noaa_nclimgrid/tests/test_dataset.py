import logging
from pathlib import Path

from pctasks.cli.cli import setup_logging, setup_logging_for_module
from pctasks.dev.test_utils import run_process_items_workflow

HERE = Path(__file__).parent
DATASET_PATH = HERE / ".." / "dataset.yaml"


# Change COG_CONTAINER in noaa_nclimgrid.py to "blob://devstoreaccount1/nclimgrid-cogs"
# to avoid saving COGs to the remote Azure container
def test_daily():
    run_process_items_workflow(
        DATASET_PATH,
        collection_id="noaa-nclimgrid-daily",
        args={
            "registry": "localhost:5001",
        },
        chunks_limit=1,
    )


def test_monthly():
    pass
    # The monthly data exists in a single set of NetCDFs (so one asset/line in
    # an asset chunkfile). So all Item and COGs for the monthly collection are
    # created from a single asset uri. This is onerous for testing. All monthly
    # data was ingested into PC Test, which more or less serves as a proxy for
    # an end-to-end integration test here.


if __name__ == "__main__":
    setup_logging(logging.DEBUG)
    setup_logging_for_module("__main__", logging.DEBUG)
    test_daily()
    print("All tests passed")
    exit(0)
