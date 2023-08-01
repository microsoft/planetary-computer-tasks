# TODO: figure out running. Just using python -m pytest for now
import json
import pathlib
import time

import azure.cosmos.exceptions
import azure.functions as func
import azure.storage.queue
import pytest
import StorageEventsCF

from pctasks.core.cosmos.containers.items import ItemsContainer
from pctasks.core.cosmos.containers.storage_events import StorageEventsContainer
from pctasks.core.models.event import StorageEvent, StorageEventRecord
from pctasks.core.models.item import StacItemRecord
from pctasks.dev.queues import TempQueue

HERE = pathlib.Path(__file__).parent


@pytest.fixture
def dispatch_rules(monkeypatch):
    """
    Update the environment with the dispatch rules.

    This reads the dispatch rules from the ``function.tf`` module in the
    deployment. It sets any app setting starting with ``PCTASKS_DISPATCH__``
    into the local environment.
    """
    p = HERE / "../../deployment/terraform/resources/function.tf"
    rule_lines = [
        x
        for x in p.read_text().split("\n")
        if x.strip().startswith('"PCTASKS_DISPATCH')
    ]
    rules = [tuple((x.strip(" '\",") for x in line.split("="))) for line in rule_lines]

    for k, v in rules:
        monkeypatch.setenv(k, v)

    yield


@pytest.fixture
def events_queue():
    body = HERE.joinpath("storage_event.json").read_text()

    with TempQueue(
        message_encode_policy=azure.storage.queue.TextBase64EncodePolicy(),
        message_decode_policy=azure.storage.queue.TextBase64DecodePolicy(),
        name="storage-events",
    ) as queue_client:
        queue_client.send_message(body)

        yield queue_client


@pytest.fixture
def goes_cmi_queue():
    with TempQueue(
        name="goes-cmi",
    ) as queue_client:
        yield queue_client


@pytest.fixture
def ingest_queue():
    """Temporary azurite queue for ingest."""
    with TempQueue(name="ingest") as queue_client:
        yield queue_client


@pytest.fixture
def msg():
    body = HERE.joinpath("storage_event.json").read_text()
    # These messages are base64 encoded in the queue. But (I think)
    # the Azure Functions runtime decodes them before building the QueueMessage
    # object
    message = func.QueueMessage(
        id="33e7bd20-117f-45e7-91e3-31e3924bd657",
        body=body,
    )
    yield message

    event_id = message.get_json()["id"]

    with StorageEventsContainer(StorageEventRecord) as cosmos_client:
        try:
            cosmos_client._cosmos_client.delete_item(event_id, event_id)
        except Exception as e:
            print(e)


@pytest.mark.parametrize(
    "url, queue_url",
    [
        (
            "https://goeseuwest.blob.core.windows.net/noaa-goes16/ABI-L2-CMIPM/2023/096/11/OR_ABI-L2-CMIPM1-M6C10_G16_s20230961135249_e20230961135321_c20230961135389.nc",  # noqa: E501
            ["goes-cmi"],
        ),
        (
            "https://goeseuwest.blob.core.windows.net/noaa-goes16/GLM-L2-LCFA/2023/213/18/OR_GLM-L2-LCFA_G16_s20232131810400_e20232131811000_c20232131811020.nc",  # noqa: E501
            ["goes-glm"],
        ),
        (
            "https://ai4edataeuwest.blob.core.windows.net/ecmwf/20230731/00z/0p4-beta/enfo/20230731000000-0h-enfo-ef.index",  # noqa: E501
            ["ecmwf-forecast"],
        ),
    ],
)
@pytest.mark.usefixtures("dispatch_rules")
def test_dispatch(url, queue_url):
    config = StorageEventsCF.load_dispatch_config()
    result = StorageEventsCF.dispatch(url, config)
    assert result == queue_url


@pytest.mark.usefixtures("dispatch_rules")
@pytest.mark.usefixtures("events_queue")
def test_storage_event_handler_integration(
    goes_cmi_queue: azure.storage.queue.QueueClient,
):
    # How is this supposed to work? Queue names are important here.
    # Storage Event -> Cosmos
    event_id = "0179968e-401e-000d-1f7b-68d814060798"
    # TODO: assert that the message is in cosmos
    deadline = time.monotonic() + 60

    with StorageEventsContainer(StorageEvent) as cosmos_client:
        try:
            while time.monotonic() < deadline:
                result = cosmos_client.get(event_id, event_id)
                if result is None:
                    print("Waiting for document")
                    time.sleep(0.5)
                else:
                    break

            assert result.id == "0179968e-401e-000d-1f7b-68d814060798"
            assert result.data.url == (
                "https://goeseuwest.blob.core.windows.net/noaa-goes16/ABI-L2-CMIPM/2023/"
                "096/11/OR_ABI-L2-CMIPM1-M6C10_G16_s20230961135249_e20230961135321_c20230961135389.nc"
            )

            while (
                goes_cmi_queue.get_queue_properties().approximate_message_count == 0
                and time.monotonic() < deadline
            ):
                print("Waiting for message")
                time.sleep(0.5)

            result_message = goes_cmi_queue.receive_message()
            event = json.loads(result_message.content)
            assert event
        finally:
            try:
                cosmos_client._container_client.delete_item(event_id, event_id)
            except azure.cosmos.exceptions.CosmosResourceNotFoundError:
                pass


def test_publish_items_cf(ingest_queue):
    body = json.loads(HERE.joinpath("stac_item_record.json").read_text())
    stac_item_record = StacItemRecord(**body)
    with ItemsContainer(StacItemRecord) as cosmos_client:
        cosmos_client.put(stac_item_record)

    deadline = time.monotonic() + 60
    while (
        ingest_queue.get_queue_properties().approximate_message_count == 0
        and time.monotonic() < deadline
    ):
        print("Waiting for message")
        time.sleep(0.5)

    message = ingest_queue.receive_message()
    result = json.loads(message.content)
    expected = body["item"]

    result["properties"].pop("updated")
    expected["properties"].pop("updated")
    assert result == expected
    ingest_queue.delete_message(message)


@pytest.mark.usefixtures("dispatch_rules")
def test_load_dispatch():
    # set up the environ

    config = StorageEventsCF.load_dispatch_config()
    assert config == [
        (
            "goes-cmi",
            "https://goeseuwest.blob.core.windows.net/noaa-goes16/ABI-L2-CMIPM/",
            None,
        ),
        (
            "goes-cmi",
            "https://goeseuwest.blob.core.windows.net/noaa-goes17/ABI-L2-CMIPM/",
            None,
        ),
        (
            "goes-cmi",
            "https://goeseuwest.blob.core.windows.net/noaa-goes18/ABI-L2-CMIPM/",
            None,
        ),
        (
            "goes-glm",
            "https://goeseuwest.blob.core.windows.net/noaa-goes16/GLM-L2-LCFA/",
            None,
        ),
        (
            "sentinel-1-grd",
            "https://sentinel1euwest.blob.core.windows.net/s1-grd/",
            "manifest.safe",
        ),
    ]
