import json
import logging
import os
import pathlib
import time
import uuid

import azure.storage.queue
import pytest
from kubernetes import client, config
from pypgstac.db import PgstacDB

from pctasks.cli.cli import setup_logging, setup_logging_for_module
from pctasks.core.cosmos.container import CosmosDBContainer
from pctasks.core.cosmos.containers.create_item_errors import CreateItemErrorsContainer
from pctasks.core.cosmos.containers.items import ItemsContainer
from pctasks.core.cosmos.containers.storage_events import StorageEventsContainer
from pctasks.core.models.event import CreateItemErrorRecord, StorageEvent
from pctasks.core.models.item import StacItemRecord
from pctasks.core.storage.blob import BlobStorage
from pctasks.core.utils import completely_flatten
from pctasks.dev.blob import copy_dir_to_azurite, temp_azurite_blob_storage
from pctasks.dev.db import ConnStrInfo, temp_pgstac_db
from pctasks.dev.queues import TempQueue
from pctasks.dev.test_utils import assert_workflow_is_successful, run_pctasks
from tests.constants import DEFAULT_TIMEOUT

HERE = pathlib.Path(__file__).parent
DATASETS = HERE
TEST_DATA = HERE / ".." / "data-files"
WORKFLOWS = HERE / ".." / "workflows"
COLLECTION_ID = "test-collection"
DEPLOYMENT_NAME = f"devstoreaccount1-{COLLECTION_ID}-deployment"
INGEST_DEPLOYMENT_NAME = "devstoreaccount1-ingest-deployment"
TEST_NAMESPACE = "argo"

setup_logging(logging.DEBUG)
setup_logging_for_module("tests.dataset.test_streaming", logging.DEBUG)
setup_logging_for_module("pctasks", logging.DEBUG)


@pytest.fixture
def cluster():
    """
    A Kubernetes cluster for the test.

    This cleans up the deployments created by the streaming test.
    """
    config.load_config()
    apps = client.AppsV1Api()
    yield
    try:
        deployment = apps.read_namespaced_deployment(
            f"azurite.10001-devstoreaccount1.{COLLECTION_ID}-stream-deployment",
            TEST_NAMESPACE,
        )
    except client.rest.ApiException as e:
        if e.status == 404:
            return
        else:
            raise e
    apps.delete_namespaced_deployment(
        deployment.metadata.name, deployment.metadata.namespace
    )


@pytest.fixture
def host_env(monkeypatch):
    """
    Some environment variables that are required on the *host* to run these tests.

    Anything that calls `run_pctasks` must set this.
    """
    env = {
        "PCTASKS_CLIENT__ENDPOINT": "http://localhost:8500/tasks",
        "PCTASKS_CLIENT__API_KEY": "kind-api-key",
        "PCTASKS_CLIENT__CONFIRMATION_REQUIRED": "false",
        "AZURITE_HOST": "localhost",
        "AZURITE_PORT": "10000",
        "AZURITE_STORAGE_ACCOUNT": "devstoreaccount1",
        "DEV_DB_CONNECTION_STRING": "postgresql://username:password@localhost:5499/postgis",  # noqa: E501
        "DEV_REMOTE_DB_CONNECTION_STRING": "postgresql://username:password@database:5432/postgis",  # noqa: E501
    }
    for k, v in env.items():
        monkeypatch.setenv(k, v)


@pytest.fixture
def cosmos_credentials():
    """Some secrets for Cosmos DB. These are provided to the task via workflow args."""
    cosmos_url = os.environ.get("PCTASKS_COSMOSDB__URL")
    if not cosmos_url:
        raise ValueError(
            "Must set 'PCTASKS_COSMOSDB__URL' in the test environment before "
            "running integration tests."
        )

    cosmos_key = os.environ.get("PCTASKS_COSMOSDB__KEY")
    if not cosmos_key:
        raise ValueError(
            "Must set 'PCTASKS_COSMOSDB__KEY' in the test environment before "
            "running integration tests."
        )
    return cosmos_url, cosmos_key


@pytest.fixture
def cleanup_kubernetes():
    config.load_config()
    apps = client.AppsV1Api()
    yield
    apps.delete_namespaced_deployment(
        f"devstoreaccount1-{COLLECTION_ID}-stream-deployment", TEST_NAMESPACE
    )


@pytest.fixture
def events_queue():
    """
    A queue for Storage Events. These messages are Base64 encoded at rest.
    """
    logging.info("Creating events queue")
    with TempQueue(
        message_encode_policy=azure.storage.queue.TextBase64EncodePolicy(),
        message_decode_policy=azure.storage.queue.TextBase64DecodePolicy(),
        name="storage-events",
    ) as queue_client:
        print(f"Created events queue at {queue_client.url}")
        yield queue_client


@pytest.fixture
def dataset_queue():
    """
    A dataset work queue with messages to create items.
    """
    logging.info("Creating dataset queue")
    dataset_queue = TempQueue(
        message_decode_policy=None,
        message_encode_policy=None,
        name=COLLECTION_ID,
    )
    with dataset_queue as queue_client:
        print(f"Created dataset queue at {queue_client.url}")
        yield queue_client


@pytest.fixture
def ingest_queue():
    logging.info("Creating ingest queue")
    ingest_queue = TempQueue(
        message_decode_policy=None, message_encode_policy=None, name="ingest"
    )
    with ingest_queue as queue_client:
        print(f"Created dataset queue at {queue_client.url}")
        yield queue_client


@pytest.fixture
def conn_str_info(host_env) -> ConnStrInfo:
    logging.info("Creating pgstac database")
    with temp_pgstac_db() as conn_str_info:
        yield conn_str_info


@pytest.fixture
def root_storage() -> BlobStorage:
    logging.info("Creating blob storage")
    with temp_azurite_blob_storage() as root_storage:
        yield root_storage


@pytest.fixture
def cosmos_storage_events_container():
    logging.info("Connecting to storage-events cosmos container")
    with StorageEventsContainer(StorageEvent) as cosmos_client:
        print(f"initialized storage-events container at {cosmos_client.name}")
        yield cosmos_client


@pytest.fixture
def cosmos_items_container():
    logging.info("Connecting to items cosmos container")
    with ItemsContainer(StacItemRecord) as cosmos_client:
        print(f"initialized items container at {cosmos_client.name}")
        yield cosmos_client


@pytest.fixture
def cosmos_create_item_errors_container():
    logging.info("Connecting to create-item-errors cosmos container")
    with CreateItemErrorsContainer(CreateItemErrorRecord) as cosmos_client:
        print(f"initialized storage-events container at {cosmos_client.name}")
        yield cosmos_client


@pytest.fixture
def ingested_collection(conn_str_info, root_storage, host_env):
    assets_storage = root_storage.get_substorage(f"{COLLECTION_ID}/assets")
    chunks_storage = root_storage.get_substorage("chunks")

    copy_dir_to_azurite(assets_storage, TEST_DATA / "assets")

    args = {
        "collection_id": COLLECTION_ID,
        "collection_template": str(TEST_DATA / "collection_template"),
        "assets_uri": assets_storage.get_uri(),
        "chunks_uri": chunks_storage.get_uri(),
        "code_path": str(HERE.resolve()),
        "db_connection_string": conn_str_info.remote,
    }

    # Ingest collection
    logging.info("Ingesting collection")
    ingest_collection_result = run_pctasks(
        [
            "dataset",
            "ingest-collection",
            "-d",
            str(HERE / "dataset.yaml"),
            "-c",
            COLLECTION_ID,
            "-u",
            "-s",
        ]
        + list(completely_flatten([["-a", k, v] for k, v in args.items()])),
    )

    assert ingest_collection_result.exit_code == 0
    ingest_collection_run_id = ingest_collection_result.output.strip()
    assert_workflow_is_successful(
        ingest_collection_run_id, timeout_seconds=DEFAULT_TIMEOUT
    )

    with PgstacDB(conn_str_info.local) as db:
        res = db.query_one(
            "SELECT id FROM collections WHERE id=%s",
            (COLLECTION_ID,),
        )
        assert res == COLLECTION_ID

    yield


@pytest.fixture
def stac_item_blob(root_storage: BlobStorage):
    body = TEST_DATA.joinpath("modis/items.ndjson").read_text().split("\n")[0]
    data = json.loads(body)
    data["collection"] = COLLECTION_ID
    root_storage.write_text("data/item.json", json.dumps(data))


@pytest.fixture
def process_items_task(dataset_queue, conn_str_info, host_env):
    process_items_result = run_pctasks(
        [
            "workflow",
            "upsert-and-submit",
            str(HERE / "streaming-create-items.yaml"),
            "--arg",
            "db_connection_string",
            conn_str_info.remote,
            "--arg",
            "queue_url",
            dataset_queue.url.replace("localhost", "azurite"),
            "--arg",
            "account_name",
            dataset_queue.credential.account_name,
            "--arg",
            "account_key",
            dataset_queue.credential.account_key,
            "--arg",
            "cosmosdb_url",
            os.environ["PCTASKS_COSMOSDB__URL"],
            "--arg",
            "cosmosdb_account_key",
            os.environ["PCTASKS_COSMOSDB__KEY"],
            "--arg",
            "test_container_suffix",
            os.environ["PCTASKS_COSMOSDB__TEST_CONTAINER_SUFFIX"],
        ]
    )
    assert process_items_result.exit_code == 0

    config.load_config()
    apps = client.AppsV1Api()
    start = time.monotonic()
    deadline = start + DEFAULT_TIMEOUT

    # Wait for the deployment
    while time.monotonic() < deadline:
        try:
            deployment = apps.read_namespaced_deployment(
                DEPLOYMENT_NAME,
                TEST_NAMESPACE,
            )
        except client.ApiException:
            print(f"Waiting for items deployment ({(time.monotonic() - start):.0f}s)")
            time.sleep(1)
            continue
        else:
            break

    start = time.monotonic()
    while deployment.status.ready_replicas != 1 and time.monotonic() < deadline:
        print(f"Waiting for items to scale up {(time.monotonic() - start):.0f}s")
        time.sleep(1)
        deployment = apps.read_namespaced_deployment(
            DEPLOYMENT_NAME,
            TEST_NAMESPACE,
        )

    deployment = apps.read_namespaced_deployment(
        DEPLOYMENT_NAME,
        TEST_NAMESPACE,
    )
    # This is eventually true
    assert deployment.status.ready_replicas == 1

    yield process_items_result

    logging.info("Deleting create items deployment")
    try:
        apps.delete_namespaced_deployment(
            deployment.metadata.name, deployment.metadata.namespace
        )
    except Exception as e:
        print(e)


@pytest.fixture
def ingest_items_task(ingest_queue, conn_str_info, host_env):
    process_items_result = run_pctasks(
        [
            "workflow",
            "upsert-and-submit",
            str(HERE / "streaming-ingest.yaml"),
            "--arg",
            "db_connection_string",
            conn_str_info.remote,
            "--arg",
            "queue_url",
            ingest_queue.url.replace("localhost", "azurite"),
            "--arg",
            "account_name",
            ingest_queue.credential.account_name,
            "--arg",
            "account_key",
            ingest_queue.credential.account_key,
            "--arg",
            "test_container_suffix",
            os.environ["PCTASKS_COSMOSDB__TEST_CONTAINER_SUFFIX"],
        ]
    )
    assert process_items_result.exit_code == 0

    config.load_config()
    apps = client.AppsV1Api()
    deadline = time.monotonic() + DEFAULT_TIMEOUT

    # Wait for the deployment
    start = time.monotonic()
    while time.monotonic() < deadline:
        try:
            deployment = apps.read_namespaced_deployment(
                INGEST_DEPLOYMENT_NAME,
                TEST_NAMESPACE,
            )
        except client.ApiException:
            print(f"Waiting for ingest deployment ({(time.monotonic() - start):.0f}s)")
            time.sleep(1)
            continue
        else:
            break

    start = time.monotonic()
    while deployment.status.available_replicas != 1 and time.monotonic() < deadline:
        print(f"Waiting for ingest to scale up {(time.monotonic() - start):.0f}s")
        time.sleep(1)
        deployment = apps.read_namespaced_deployment(
            INGEST_DEPLOYMENT_NAME,
            TEST_NAMESPACE,
        )

    deployment = apps.read_namespaced_deployment(
        INGEST_DEPLOYMENT_NAME,
        TEST_NAMESPACE,
    )
    # This is eventually true
    assert deployment.status.ready_replicas == 1

    yield

    try:
        apps.delete_namespaced_deployment(
            deployment.metadata.name, deployment.metadata.namespace
        )
    except Exception as e:
        print(e)


@pytest.fixture
def core_api(cluster):
    config.load_kube_config()
    return client.CoreV1Api()


def print_status(core_api: client.CoreV1Api, label_selector: str) -> None:
    pods = core_api.list_namespaced_pod(TEST_NAMESPACE, label_selector=label_selector)
    print("Listing pod status...")

    for pod in pods.items:
        s = f" Pod: {pod.metadata.name} [{pod.status.phase}] "
        print(f"{s:-^80}")
        if pod.status.phase == "Running":
            for line in core_api.read_namespaced_pod_log(
                pod.metadata.name, pod.metadata.namespace, since_seconds=5
            ).splitlines():
                print(f"\t{line}")

    print("=" * 80)


@pytest.mark.usefixtures(
    "cluster",
    "cosmos_credentials",
    "cosmosdb_containers",
    "dataset_queue",
    "ingest_queue",
    "ingested_collection",
    "stac_item_blob",
    "ingest_items_task",
)
def test_streaming(
    events_queue,
    conn_str_info,
    root_storage,
    cosmos_storage_events_container,
    cosmos_items_container,
    cosmos_create_item_errors_container,
    core_api,
    process_items_task,
):
    """
    An end-to-end integration test for streaming workloads.

    This exercises the entire pipeline, from a Blob Storage Event in
    a storage queue to a STAC item in a pgstac database. It covers the
    following stages:

    1. An EventGrid message is written to a `storage-events` queue
    2. An (emulated) Azure Function forwards the message to Cosmos DB
    3. An (emulated) Azure Function monitoring the Cosmos DB Change Feed
       forwards the message to the dataset work queue
    4. The pctasks streaming task processes the message from the queue,
       writing the output to Cosmos DB
    5. An (emulated0) Azure Function monitoring the Cosmos DB Change Feed
       forwards the completed STAC item to the ingest queue
    6. The pctasks streaming ingest task ingests the STAC item into the
       pgstac database

    Prerequisites
    -------------

    The prerequisites are put into pytest fixtures. As much as possible,
    we want this test to focus on triggering the pipeline and asserting
    outputs at various observable stages.

    - pctasks_funcs
    - A Cosmos DB database (probably the one set up for CI) with
        - a storage-events container
        - a items container
    - A pgstac database
    - A STAC collection in that pgstac database named 'test-collection'
    - A bunch of queues in Azurite, including
        - storage-events
        - dataset
        - ingest
    - A Blob in the Storage Container with the item JSON
    - A streaming create items task in the Kind Kubernetes cluster
    - A streaming ingest items task in the Kind Kubernetes cluster
    """
    event = StorageEvent(
        id="0179968e-401e-000d-1f7b-68d814060798",
        source="/subscriptions/1b045d0d-e560-456a-952d-7514f87f1b1f/resourceGroups/goes-rg/providers/Microsoft.Storage/storageAccounts/goeseuwest",  # noqa: E501
        specversion="1.0",
        type="Microsoft.Storage.BlobCreated",
        subject="/blobServices/default/containers/noaa-goes16/blobs/ABI-L2-CMIPM/2023/096/11/OR_ABI-L2-CMIPM1-M6C10_G16_s20230961135249_e20230961135321_c20230961135389.nc",  # noqa: E501
        time="2023-04-06T11:35:54.6001153Z",
        data={
            "api": "PutBlob",
            "clientRequestId": "30755694-d46f-11ed-856d-02420a0007ba",
            "requestId": "0179968e-401e-000d-1f7b-68d814000000",
            "eTag": "0x8DB369315269B01",
            "contentType": "application/octet-stream",
            "contentLength": 343897,
            "blobType": "BlockBlob",
            # This will be read from a Kubernetes pod, so use `azurite` not `localhost`
            "url": root_storage.get_url("data/item.json").replace(
                "localhost", "azurite"
            ),
            "sequencer": "0000000000000000000000000000ECA5000000000000c808",
            "storageDiagnostics": {"batchId": "b57dab2b-4006-001d-007b-68e98f000000"},
        },
    )

    # OK, now we're all ready to go!
    # Submit an event. Azure Function will move that to Cosmos DB
    event_id = str(uuid.uuid4())
    event.id = event_id

    events_queue.send_message(event.json())

    # This triggers
    # 1. The StorageEventsQueue Azure Function -> Cosmos DB
    # 2. The StorageEventsCF Azure Function -> `goes-cmi` queue

    # ----------------------------------------------------------------------------
    # Create Items
    # Submit the task to start the process items deployment

    # Checkpoint 1: the event is in Cosmos DB
    result = wait_for_document(event_id, event_id, cosmos_storage_events_container)

    # Checkpoint 2: The asset has been processed. The item is in Cosmos DB
    # Azure Function will forward from Cosmos -> dataset queue
    # Then our pctasks task will process it.
    # stac_id = "test-collection/MOD14A1.A2000049.h00v08.061.2020041150332"
    # TODO: add some random thing to  this ID and delete after test run.

    document_id = f"{COLLECTION_ID}:MOD14A1.A2000049.h00v08.061.2020041150332::StacItem"
    stac_id = f"{COLLECTION_ID}/MOD14A1.A2000049.h00v08.061.2020041150332"
    start = time.monotonic()
    label_selector = (
        "planetarycomputer.microsoft.com/queue_url=devstoreaccount1-test-collection"
    )
    result = wait_for_document(document_id, stac_id, cosmos_items_container)
    print("Item is in Cosmos DB")

    # Checkpoint 3: The item has been ingested into pgstac

    # ----------------------------------------------------------------------------
    # Ingest Items

    start = time.monotonic()
    deadline = start + DEFAULT_TIMEOUT
    label_selector = "planetarycomputer.microsoft.com/queue_url=devstoreaccount1-ingest"

    with PgstacDB(conn_str_info.local) as db:
        while time.monotonic() < deadline:
            res = db.search(
                {
                    "filter": {
                        "op": "=",
                        "args": [{"property": "collection"}, COLLECTION_ID],
                    }
                }
            )
            assert isinstance(res, str)
            features = json.loads(res)["features"]

            if len(features) == 0:
                print(
                    f"Waiting for pgstac ingest at {conn_str_info.local} "
                    f"{(time.monotonic() - start):.0f}s"
                )
                print_status(core_api, label_selector=label_selector)
                time.sleep(5)
            else:
                break
        else:
            raise AssertionError("Timeout getting pgstac item.")

    print("Item is in PgSTAC")
    feature = features[0]
    assert feature

    process_items_run_id = process_items_task.output.strip()

    # Try a failure now. Point the user-defined function at a non-existent URL
    event_id = str(uuid.uuid4())
    event.data.url = event.data.url.replace("item.json", "item2.json")
    event.id = event_id
    events_queue.send_message(event.json())

    document_id = f"{event_id}:{process_items_run_id}:1"
    # The user-defined create item function should have been called and gotten a 404
    # from Blob Storage.
    # The item should be in the create-items-errors container in Cosmos DB
    result = wait_for_document(
        document_id, document_id, cosmos_create_item_errors_container
    )
    assert result is not None
    assert result.type == "CreateItemError"
    assert "FileNotFoundError:" in result.traceback.strip().split("\n")[-1]
    assert result.attempt == 1
    assert result.run_id == process_items_run_id


def wait_for_document(
    id: str, partition_key: str, cosmos_container: CosmosDBContainer, timeout: int = 60
):
    start = time.monotonic()
    deadline = start + timeout
    key = f"{partition_key}/{id}"
    while time.monotonic() < deadline:
        try:
            result = cosmos_container.get(id, partition_key)
            if result is None:
                raise KeyError(f"Document '{key}' not found")
        except Exception:
            print(f"Waiting for document '{key}' {(time.monotonic() - start):.0f}s")
            time.sleep(0.5)
        else:
            break
    else:
        raise AssertionError(f"Timeout getting document '{key}'")
    print(f"Storage Event '{key}' is in Cosmos DB")
    return result
