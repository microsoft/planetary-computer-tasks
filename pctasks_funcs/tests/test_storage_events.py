# TODO: figure out running. Just using python -m pytest for now
import base64
import json
import pathlib
import time

import azure.cosmos.exceptions
import azure.functions as func
import azure.storage.queue
import pytest
import StorageEventsCF
import StorageEventsQueue

from pctasks.core.cosmos.containers.items import ItemsContainer
from pctasks.core.cosmos.containers.storage_events import StorageEventsContainer
from pctasks.core.models.event import StorageEvent, StorageEventRecord
from pctasks.core.models.item import StacItemRecord
from pctasks.dev.queues import TempQueue

HERE = pathlib.Path(__file__).parent


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
            "goes-cmi",
        ),
    ],
)
def test_dispatch(url, queue_url):
    result = StorageEventsCF.dispatch(url)
    assert result == queue_url


def test_storage_event_handler_integration(
    events_queue, goes_cmi_queue: azure.storage.queue.QueueClient
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
