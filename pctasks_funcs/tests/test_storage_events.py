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
        name="test-collection",
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
            "https://goeseuwest.blob.core.windows.net/noaa-goes18/ABI-L2-MCMIPC/2023/216/12/OR_ABI-L2-MCMIPC-M6_G18_s20232161201191_e20232161203570_c20232161204083.nc",  # noqa: E501
            ["goes-cmi"],
        ),
        (
            "https://goeseuwest.blob.core.windows.net/noaa-goes18/ABI-L2-MCMIPM/2023/216/11/OR_ABI-L2-MCMIPM2-M6_G18_s20232161147570_e20232161148039_c20232161148111.nc",  # noqa: E501
            ["goes-cmi"],
        ),
        (
            "https://goeseuwest.blob.core.windows.net/noaa-goes18/ABI-L2-MCMIPF/2023/216/13/OR_ABI-L2-MCMIPF-M6_G18_s20232161310226_e20232161319545_c20232161320015.nc",  # noqa: E501
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
        (
            "http://azurite:10000/devstoreaccount1/test-data/test-be972b3430ac11eebe9b00155d300a6b/data/item.json",  # noqa: E501
            ["test-collection"],
        ),
        (
            "http://azurite:10000/devstoreaccount1/ABI-L2-CMIPM/2023/096/11/OR_ABI-L2-CMIPM1-M6C10_G16_s20230961135249_e20230961135321_c20230961135389.nc",  # noqa: E501,
            ["test-collection"],
        ),
        (
            "https://landsateuwest.blob.core.windows.net/landsat-c2/level-2/standard/oli-tirs/2023/022/028/LC09_L2SP_022028_20230731_20230802_02_T1/LC09_L2SP_022028_20230731_20230802_02_T1_MTL.xml",  # noqa: E501
            ["landsat-c2-l2"],
        ),
        (
            "https://modiseuwest.blob.core.windows.net/modis-061/MOD09A1/00/08/2000049/MOD09A1.A2000049.h00v08.061.2020041195232.hdf",
            ["modis-09a1-061"],
        ),
        (
            "https://modiseuwest.blob.core.windows.net/modis-061/MYD09A1/00/08/2002185/MYD09A1.A2002185.h00v08.061.2020072151743.hdf",
            ["modis-09a1-061"],
        ),
        (
            "https://modiseuwest.blob.core.windows.net/modis-061/MCD15A2H/00/08/2002185/MCD15A2H.A2002185.h00v08.061.2020079150825.hdf",
            ["modis-15a2h-061"],
        ),
        (
            "https://modiseuwest.blob.core.windows.net/modis-061/MOD15A2H/00/08/2000049/MOD15A2H.A2000049.h00v08.061.2020041201434.hdf",
            ["modis-15a2h-061"],
        ),
        (
            "https://modiseuwest.blob.core.windows.net/modis-061/MYD15A2H/00/08/2002185/MYD15A2H.A2002185.h00v08.061.2020072153807.hdf",
            ["modis-15a2h-061"],
        ),
        (
            "https://modiseuwest.blob.core.windows.net/modis-061/MCD15A3H/00/08/2002185/MCD15A3H.A2002185.h00v08.061.2020076202807.hdf",
            ["modis-15a3h-061"],
        ),
        (
            "https://modiseuwest.blob.core.windows.net/modis-061/MCD43A4/00/08/2000055/MCD43A4.A2000055.h00v08.061.2020038135030.hdf",
            ["modis-43a4-061"],
        ),
        (
            "https://modiseuwest.blob.core.windows.net/modis-061/MCD64A1/00/08/2000032/MCD64A1.A2000032.h00v08.061.2021307215218.hdf",
            ["modis-64a1-061"],
        ),
        (
            "https://modiseuwest.blob.core.windows.net/modis-061/MOD09Q1/00/08/2000049/MOD09Q1.A2000049.h00v08.061.2020041195232.hdf",
            ["modis-09q1-061"],
        ),
        (
            "https://modiseuwest.blob.core.windows.net/modis-061/MYD09Q1/00/08/2002185/MYD09Q1.A2002185.h00v08.061.2020072151743.hdf",
            ["modis-09q1-061"],
        ),
        (
            "https://modiseuwest.blob.core.windows.net/modis-061/MOD10A1/00/08/2000055/MOD10A1.A2000055.h00v08.061.2020037170654.hdf",
            ["modis-10a1-061"],
        ),
        (
            "https://modiseuwest.blob.core.windows.net/modis-061/MYD10A1/00/08/2002185/MYD10A1.A2002185.h00v08.061.2020071172435.hdf",
            ["modis-10a1-061"],
        ),
        (
            "https://modiseuwest.blob.core.windows.net/modis-061/MOD10A2/00/08/2000049/MOD10A2.A2000049.h00v08.061.2020041202454.hdf",
            ["modis-10a2-061"],
        ),
        (
            "https://modiseuwest.blob.core.windows.net/modis-061/MYD10A2/00/08/2002185/MYD10A2.A2002185.h00v08.061.2020072154626.hdf",
            ["modis-10a2-061"],
        ),
        (
            "https://modiseuwest.blob.core.windows.net/modis-061/MOD11A1/00/08/2000055/MOD11A1.A2000055.h00v08.061.2020043121122.hdf",
            ["modis-11a1-061"],
        ),
        (
            "https://modiseuwest.blob.core.windows.net/modis-061/MYD11A1/00/08/2002186/MYD11A1.A2002186.h00v08.061.2020128174537.hdf",
            ["modis-11a1-061"],
        ),
        (
            "https://modiseuwest.blob.core.windows.net/modis-061/MOD11A2/00/08/2000049/MOD11A2.A2000049.h00v08.061.2020048120244.hdf",
            ["modis-11a2-061"],
        ),
        (
            "https://modiseuwest.blob.core.windows.net/modis-061/MYD11A2/00/08/2002185/MYD11A2.A2002185.h00v08.061.2020140130634.hdf",
            ["modis-11a2-061"],
        ),
        (
            "https://modiseuwest.blob.core.windows.net/modis-061/MOD13A1/00/08/2000049/MOD13A1.A2000049.h00v08.061.2020041151322.hdf",
            ["modis-13a1-061"],
        ),
        (
            "https://modiseuwest.blob.core.windows.net/modis-061/MYD13A1/00/08/2002185/MYD13A1.A2002185.h00v08.061.2020072153221.hdf",
            ["modis-13a1-061"],
        ),
        (
            "https://modiseuwest.blob.core.windows.net/modis-061/MOD13Q1/00/08/2000049/MOD13Q1.A2000049.h00v08.061.2020041152316.hdf",
            ["modis-13q1-061"],
        ),
        (
            "https://modiseuwest.blob.core.windows.net/modis-061/MYD13Q1/00/08/2002185/MYD13Q1.A2002185.h00v08.061.2020072153805.hdf",
            ["modis-13q1-061"],
        ),
        (
            "https://modiseuwest.blob.core.windows.net/modis-061/MOD14A1/00/08/2000049/MOD14A1.A2000049.h00v08.061.2020041150332.hdf",
            ["modis-14a1-061"],
        ),
        (
            "https://modiseuwest.blob.core.windows.net/modis-061/MYD14A1/00/08/2002185/MYD14A1.A2002185.h00v08.061.2020072112803.hdf",
            ["modis-14a1-061"],
        ),
        (
            "https://modiseuwest.blob.core.windows.net/modis-061/MOD14A2/00/08/2000049/MOD14A2.A2000049.h00v08.061.2020041150332.hdf",
            ["modis-14a2-061"],
        ),
        (
            "https://modiseuwest.blob.core.windows.net/modis-061/MYD14A2/00/08/2002185/MYD14A2.A2002185.h00v08.061.2020072112803.hdf",
            ["modis-14a2-061"],
        ),
        (
            "https://modiseuwest.blob.core.windows.net/modis-061/MOD16A3GF/00/08/2000049/MOD16A3GF.A2000001.h00v08.061.2020264071747.hdf",
            ["modis-16a3gf-061"],
        ),
        (
            "https://modiseuwest.blob.core.windows.net/modis-061/MYD16A3GF/00/08/2002185/MYD16A3GF.A2002001.h00v08.061.2020301203818.hdf",
            ["modis-16a3gf-061"],
        ),
        (
            "https://modiseuwest.blob.core.windows.net/modis-061/MOD17A2H/00/08/2021001/MOD17A2H.A2021001.h00v08.061.2021069214628.hdf",
            ["modis-17a2h-061"],
        ),
        (
            "https://modiseuwest.blob.core.windows.net/modis-061/MYD17A2H/00/08/2021001/MYD17A2H.A2021001.h00v08.061.2021069223256.hdf",
            ["modis-17a2h-061"],
        ),
        (
            "https://modiseuwest.blob.core.windows.net/modis-061/MOD17A2HGF/00/08/2000009/MOD17A2HGF.A2000009.h00v08.061.2020125224802.hdf",
            ["modis-17a2hgf-061"],
        ),
        (
            "https://modiseuwest.blob.core.windows.net/modis-061/MYD17A2HGF/00/08/2002001/MYD17A2HGF.A2002001.h00v08.061.2020167185801.hdf",
            ["modis-17a2hgf-061"],
        ),
        (
            "https://modiseuwest.blob.core.windows.net/modis-061/MOD17A3HGF/00/08/2001001/MOD17A3HGF.A2001001.h00v08.061.2020136134928.hdf",
            ["modis-17a3hgf-061"],
        ),
        (
            "https://modiseuwest.blob.core.windows.net/modis-061/MYD17A3HGF/00/08/2002185/MYD17A3HGF.A2002001.h00v08.061.2020170193809.hdf",
            ["modis-17a3hgf-061"],
        ),
        (
            "https://modiseuwest.blob.core.windows.net/modis-061/MOD21A2/00/08/2000049/MOD21A2.A2000049.h00v08.061.2020041203631.hdf",
            ["modis-21a2-061"],
        ),
        (
            "https://modiseuwest.blob.core.windows.net/modis-061/MYD21A2/00/08/2002185/MYD21A2.A2002185.h00v08.061.2020072155503.hdf",
            ["modis-21a2-061"],
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
                "http://azurite:10000/devstoreaccount1/ABI-L2-CMIPM/2023/"
                "096/11/OR_ABI-L2-CMIPM1-M6C10_G16_s20230961135249_e20230961135321_c20230961135389.nc"  # noqa: E501
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
