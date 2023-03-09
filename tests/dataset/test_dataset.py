import datetime
import json
import logging
import os
import time
from pathlib import Path
from uuid import uuid1

import pystac
import pytest
from kubernetes import client, config
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


@pytest.fixture
def cluster():
    config.load_config()
    apps = client.AppsV1Api()
    yield
    try:
        deployment = apps.read_namespaced_deployment(
            "azurite.10001-devstoreaccount1.test-queue-stream-deployment", "argo"
        )
    except client.rest.ApiException as e:
        if e.status == 404:
            return
        else:
            raise e
    apps.delete_namespaced_deployment(
        deployment.metadata.name, deployment.metadata.namespace
    )


def test_streaming(cluster):
    """
    An integration test for streaming workloads. This will

    1. Create a dataset work queue, ingest queue using azurite
    2. Push a batch of messages onto the queue
    3. Create a Kubernetes Deployment, KEDA scaled object to
        - process messages from the dataset queue
        - ingest messages from the ingest queue
    """
    # how does the networking work?
    # Is there any way for a Kubernetes pod to see azurite? I think not?
    dataset_queue = TempQueue(
        message_decode_policy=None, message_encode_policy=None, suffix="stream"
    )
    ingest_queue = TempQueue(
        message_decode_policy=None, message_encode_policy=None, suffix="ingest"
    )
    with (
        temp_pgstac_db() as conn_str_info,
        dataset_queue as dataset_queue_client,
        ingest_queue,
        temp_azurite_blob_storage() as root_storage,  # noqa
    ):
        dataset_queue_client.send_message(
            json.dumps(
                {
                    "data": {
                        "url": pystac.Item(
                            "id", {}, None, datetime.datetime(2000, 1, 1), {}
                        ).to_dict()
                    },
                    "time": "2019-11-18T15:13:39.4589254Z",
                    "id": "9aeb0fdf-c01e-0131-0922-9eb54906e209",
                }
            )
        )

        # Process items
        process_items_result = run_pctasks(
            [
                "workflow",
                "upsert-and-submit",
                str(HERE / "streaming-create-items.yaml"),
                "--arg",
                "db_connection_string",
                conn_str_info.remote,
                "--arg",
                "cosmos_endpoint",
                os.environ["PCTASKS_COSMOSDB__URL"],
                "--arg",
                "cosmos_credential",
                os.environ["PCTASKS_COSMOSDB__KEY"],
                "--arg",
                "queue_url",
                dataset_queue_client.url.replace("localhost", "azurite"),
                "--arg",
                "account_name",
                dataset_queue_client.credential.account_name,
                "--arg",
                "account_key",
                dataset_queue_client.credential.account_key,
            ]
        )
        assert process_items_result.exit_code == 0

        # Ingest items
        config.load_config()
        apps = client.AppsV1Api()
        deadline = time.monotonic() + TIMEOUT_SECONDS

        while time.monotonic() < deadline:
            try:
                deployment = apps.read_namespaced_deployment(
                    "azurite.10001-devstoreaccount1.test-queue-stream-deployment",
                    "argo",
                )
            except client.ApiException:
                print("waiting for deployment")
                time.sleep(1)
                continue

            while deployment.status.available_replicas != 1:
                time.sleep(1)
                deployment = apps.read_namespaced_deployment(
                    "azurite.10001-devstoreaccount1.test-queue-stream-deployment",
                    "argo",
                )

            # This is eventually true
            assert deployment.status.available_replicas == 1

            # This is eventually true
            while (
                dataset_queue_client.get_queue_properties()["approximate_message_count"]
                > 0
            ):
                print("waiting for queue")
                time.sleep(1)

            break
        # TODO: ingest collection
        # process_items_result = run_pctasks(
        #     [
        #         "workflow"
        #         "upsert-and-submit",
        #         str(HERE / "streaming-ingest.yaml"),
        #         "--arg",
        #         "db_connection_string",
        #         conn_str_info.remote,
        #         "--arg",
        #         "cosmos_endpoint",
        #         os.environ["PCTASKS_COSMOSDB__URL"],
        #         "--arg",
        #         "cosmos_credential",
        #         os.environ["PCTASKS_COSMOSDB__KEY"],
        #         "--arg",
        #         "queue_url",
        #         dataset_queue_client.url.replace("localhost", "azurite"),
        #         "--arg",
        #         "account_name",
        #         dataset_queue_client.credential.account_name,
        #         "--arg",
        #         "account_key",
        #         dataset_queue_client.credential.account_key,
        #     ]
        # )
        # assert process_items_result.exit_code == 0

        # TODO: create streaming items ingest deployment

    # TODO: cleanup the Kubernetes stuff


if __name__ == "__main__":
    setup_logging(logging.DEBUG)
    setup_logging_for_module("__main__", logging.DEBUG)
    test_dataset()
    print("All tests passed")
    exit(0)
