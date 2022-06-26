import json
import logging
import textwrap
from pathlib import Path

from pctasks.cli.cli import setup_logging, setup_logging_for_module
from pctasks.dev.blob import temp_azurite_blob_storage
from pctasks.dev.db import temp_pgstac_db
from pctasks.dev.test_utils import (
    assert_workflow_is_successful,
    run_workflow,
    run_workflow_from_file,
)

HERE = Path(__file__).parent
COLLECTION_PATH = HERE / ".." / "data-files/modis/collection.json"
NDJSON_PATH = HERE / ".." / "data-files/modis/items.ndjson"
WORKFLOWS = HERE / ".." / "workflows"

TIMEOUT_SECONDS = 60


def test_modis_ingest() -> None:
    with temp_pgstac_db() as conn_str:
        # Ingest collection

        collection_path = HERE / ".." / "data-files" / "modis" / "collection.json"
        with collection_path.open() as f:
            collection = json.load(f)
        run_id = run_workflow_from_file(
            WORKFLOWS / "ingest-collection.yaml",
            args={"collection": collection, "db_connection_str": conn_str},
        )
        assert_workflow_is_successful(run_id, timeout_seconds=TIMEOUT_SECONDS)

        # Process items

        with temp_azurite_blob_storage(NDJSON_PATH) as storage:

            items_workflow = textwrap.dedent(
                """\
                name: Ingest Items Test Workflow
                dataset: microsoft/modis-test

                args:
                - ndjson_uri
                - db_conn_str

                jobs:
                    ingest:
                        name: Ingest Items
                        tasks:
                        - id: ingest-items
                          image: localhost:5001/pctasks-ingest:latest
                          task: pctasks.ingest_task.task:ingest_task
                          environment:
                            DB_CONNECTION_STRING: "${{ args.db_conn_str }}"
                          args:
                            content:
                                type: Ndjson
                                uris:
                                - ${{ args.ndjson_uri }}


                """
            )

            items_run_id = run_workflow(
                items_workflow,
                args={
                    "ndjson_uri": storage.get_uri("items.ndjson"),
                    "db_conn_str": conn_str,
                },
            )

            assert_workflow_is_successful(items_run_id, timeout_seconds=TIMEOUT_SECONDS)


if __name__ == "__main__":
    setup_logging(logging.DEBUG)
    setup_logging_for_module("__main__", logging.DEBUG)
    test_modis_ingest()
    print("All tests passed")
    exit(0)
