from datetime import date
import logging

from datasets.modis.modis import MODISCollection, add_platform_field
from pctasks.core.storage import StorageFactory
from pystac import Item

logger = logging.getLogger(__name__)


def test_terra() -> None:
    href = "https://modiseuwest.blob.core.windows.net/modis-061/MOD14A2/19/05/2024033/MOD14A2.A2024033.h19v05.061.2024044033426.hdf.xml"
    item = Item(
        id="MOD14A2.A2024033.h19v05.061.2024044033426",
        properties={},
        geometry=None,
        bbox=None,
        datetime=date.today(),
    )
    item = add_platform_field(item, href, logger)
    assert item.properties["platform"] == "terra"


def test_aqua() -> None:
    href = "https://modiseuwest.blob.core.windows.net/modis-061/MYD14A2/20/05/2024033/MYD14A2.A2024033.h20v05.061.2024043110139.hdf.xml"
    item = Item(
        id="MOD14A2.A2024033.h19v05.061.2024044033426",
        properties={},
        geometry=None,
        bbox=None,
        datetime=date.today(),
    )
    item = add_platform_field(item, href, logger)
    assert item.properties["platform"] == "aqua"


def test_malformed_href() -> None:
    href = "asdasdaasdasdads"
    item = Item(
        id="MOD14A2.A2024033.h19v05.061.2024044033426",
        properties={},
        geometry=None,
        bbox=None,
        datetime=date.today(),
    )
    item = add_platform_field(item, href, logger)


def test_create_mcd64a1_item() -> None:
    asset_uri = (
        "blob://modiseuwest/modis-061/MCD64A1/35/09/2025182/"
        "MCD64A1.A2025182.h35v09.061.2025258150345.hdf"
    )

    (item,) = MODISCollection.create_item(asset_uri, StorageFactory())

    assert item.id == "MCD64A1.A2025182.h35v09.061.2025258150345"
    assert item.properties["platform"] == "terra,aqua"
    item.validate()
