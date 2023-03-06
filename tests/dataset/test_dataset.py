import json
import logging
import os
from pathlib import Path
from uuid import uuid1

from pypgstac.db import PgstacDB

from pctasks.cli.cli import setup_logging, setup_logging_for_module
from pctasks.core.utils import completely_flatten
from pctasks.dev.blob import copy_dir_to_azurite, temp_azurite_blob_storage
from pctasks.dev.db import temp_pgstac_db
from pctasks.dev.queues import TempQueue
from pctasks.dev.test_utils import assert_workflow_is_successful, run_pctasks
from tests.constants import DEFAULT_TIMEOUT

HERE = Path(__file__).parent
DATASETS = HERE
TEST_DATA = HERE / ".." / "data-files"
WORKFLOWS = HERE / ".." / "workflows"

TIMEOUT_SECONDS = DEFAULT_TIMEOUT


def test_dataset():
    with temp_pgstac_db() as conn_str_info:
        test_tag = uuid1().hex[:5]
        collection_id = "test-collection"

        with temp_azurite_blob_storage() as root_storage:
            assets_storage = root_storage.get_substorage(f"{collection_id}/assets")
            chunks_storage = root_storage.get_substorage("chunks")

            copy_dir_to_azurite(assets_storage, TEST_DATA / "assets")

            args = {
                "collection_id": collection_id,
                "collection_template": str(TEST_DATA / "collection_template"),
                "assets_uri": assets_storage.get_uri(),
                "chunks_uri": chunks_storage.get_uri(),
                "code_path": str(HERE.resolve()),
                "db_connection_string": conn_str_info.remote,
            }

            # Ingest collection

            ingest_collection_result = run_pctasks(
                [
                    "dataset",
                    "ingest-collection",
                    "-d",
                    str(HERE / "dataset.yaml"),
                    "-c",
                    collection_id,
                    "-u",
                    "-s",
                ]
                + list(completely_flatten([["-a", k, v] for k, v in args.items()])),
            )

            assert ingest_collection_result.exit_code == 0
            ingest_collection_run_id = ingest_collection_result.output.strip()
            assert_workflow_is_successful(
                ingest_collection_run_id, timeout_seconds=TIMEOUT_SECONDS
            )

            with PgstacDB(conn_str_info.local) as db:
                res = db.query_one(
                    "SELECT id FROM collections WHERE id=%s",
                    (collection_id,),
                )
                assert res == collection_id

            # Process items

            process_items_result = run_pctasks(
                [
                    "dataset",
                    "process-items",
                    "-d",
                    str(HERE / "dataset.yaml"),
                    "-c",
                    collection_id,
                    "test-" + test_tag,
                    "-s",
                ]
                + list(completely_flatten([["-a", k, v] for k, v in args.items()])),
            )

            assert process_items_result.exit_code == 0
            process_items_run_id = process_items_result.output.strip()
            assert_workflow_is_successful(
                process_items_run_id, timeout_seconds=TIMEOUT_SECONDS
            )

            with PgstacDB(conn_str_info.local) as db:
                res = db.search(
                    {
                        "filter": {
                            "op": "=",
                            "args": [{"property": "collection"}, collection_id],
                        }
                    }
                )
                assert isinstance(res, str)
                assert json.loads(res)["features"]


def test_streaming():
    with (
        temp_pgstac_db() as conn_str_info,
        TempQueue(
            message_decode_policy=None, message_encode_policy=None, suffix="stream"
        ) as queue_client,
        temp_azurite_blob_storage() as root_storage,
    ):
        collection_id = "test-collection"

        # put some messages on the queue
        for i in range(10):
            queue_client.send_message(json.dumps({"data": {"url": f"test-{i}.tif"}}))

        args = {
            "collection_id": collection_id,
            "collection_template": str(TEST_DATA / "collection_template"),
            "code_path": str(HERE.resolve()),
            "db_connection_string": conn_str_info.remote,
        }

        # Ingest collection

        ingest_collection_result = run_pctasks(
            [
                "dataset",
                "ingest-collection",
                "-d",
                str(HERE / "dataset.yaml"),
                "-c",
                collection_id,
                "-u",
                "-s",
            ]
            + list(completely_flatten([["-a", k, v] for k, v in args.items()])),
        )

        assert ingest_collection_result.exit_code == 0
        ingest_collection_run_id = ingest_collection_result.output.strip()
        assert_workflow_is_successful(
            ingest_collection_run_id, timeout_seconds=TIMEOUT_SECONDS
        )

        with PgstacDB(conn_str_info.local) as db:
            res = db.query_one(
                "SELECT id FROM collections WHERE id=%s",
                (collection_id,),
            )
            assert res == collection_id

        # Process items

        process_items_result = run_pctasks(
            [
                "workflow",
                "upsert-and-submit",
                str(HERE / "dataset-streaming.yaml"),
                "--arg",
                "db_connection_string",
                conn_str_info.remote,
                "--arg",
                "cosmos_endpoint",
                os.environ["PCTASKS_COSMOSDB__URL"],
                "cosmos_credential",
                os.environ["PCTASKS_COSMOSDB__KEY"],
            ]
        )

        assert process_items_result.exit_code == 0
        process_items_run_id = process_items_result.output.strip()
        assert_workflow_is_successful(
            process_items_run_id, timeout_seconds=TIMEOUT_SECONDS
        )

        with PgstacDB(conn_str_info.local) as db:
            res = db.search(
                {
                    "filter": {
                        "op": "=",
                        "args": [{"property": "collection"}, collection_id],
                    }
                }
            )
            assert isinstance(res, str)
            assert json.loads(res)["features"]


if __name__ == "__main__":
    setup_logging(logging.DEBUG)
    setup_logging_for_module("__main__", logging.DEBUG)
    test_dataset()
    print("All tests passed")
    exit(0)
