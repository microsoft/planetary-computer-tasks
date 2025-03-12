import logging
from datasets.modis.misc import add_platform_field
from pystac import Item
from datetime import date

logger = logging.getLogger(__name__)

def test_terra():
    href = 'https://modiseuwest.blob.core.windows.net/modis-061/MOD14A2/19/05/2024033/MOD14A2.A2024033.h19v05.061.2024044033426.hdf.xml'
    item = Item(id="MOD14A2.A2024033.h19v05.061.2024044033426", properties={}, geometry=None, bbox=None, datetime=date.today())
    item = add_platform_field(item, href, logger)
    assert item.properties["platform"] == "terra"

def test_aqua():
    href = 'https://modiseuwest.blob.core.windows.net/modis-061/MYD14A2/20/05/2024033/MYD14A2.A2024033.h20v05.061.2024043110139.hdf.xml'
    item = Item(id="MOD14A2.A2024033.h19v05.061.2024044033426", properties={}, geometry=None, bbox=None, datetime=date.today())
    item = add_platform_field(item, href, logger)
    assert item.properties["platform"] == "aqua"

def test_malformed_href():
    href = 'asdasdaasdasdads'
    item = Item(id="MOD14A2.A2024033.h19v05.061.2024044033426", properties={}, geometry=None, bbox=None, datetime=date.today())
    item = add_platform_field(item, href, logger)
