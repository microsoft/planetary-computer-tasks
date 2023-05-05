import pytest
from naip import NAIPCollection
from pctasks.core.storage import StorageFactory


@pytest.mark.parametrize(
    "href",
    [
        "blob://naipeuwest/naip/v002/wa/2021/wa_060cm_2021/45116/m_4511601_ne_11_060_20210629.tif",  # noqa: E501
        "blob://naipeuwest/naip/v002/co/2021/co_060cm_2021/37102/63/m_3710263_sw_13_060_20210729.tif"  # noqa: E501
    ],
)
def test_naip(href):
    storage_factory = StorageFactory()
    (item,) = NAIPCollection.create_item(href, storage_factory, upload=False)
    item.validate()
    assert "grid:code" not in item.properties
    assert "raster:bands" not in item.assets["image"].extra_fields
    assert item.stac_extensions == [
        "https://stac-extensions.github.io/eo/v1.0.0/schema.json",
        "https://stac-extensions.github.io/projection/v1.0.0/schema.json",
    ]
    if "/63/" in href:
        # verify that the new item ID includes both area & subarea
        assert item.id == "co_m_3710263_sw_13_060_20210729"
