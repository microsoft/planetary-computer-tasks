import pytest
from naip import NAIPCollection
from pctasks.core.storage import StorageFactory


@pytest.mark.parametrize(
    "href",
    [
        "blob://naipeuwest/naip/v002/wa/2021/wa_060cm_2021/45116/m_4511601_ne_11_060_20210629.tif",  # noqa: E501
        "blob://naipeuwest/naip/v002/co/2021/co_060cm_2021/37102/63/m_3710263_sw_13_060_20210729.tif",  # noqa: E501
        "blob://naipeuwest/naip/v002/ca/2022/ca_060cm_2022/41120/m_4112001_sw_10_060_20220716.tif",  # noqa: E501
        "blob://naipeuwest/naip/v002/ca/2022/ca_030cm_2022/41120/m_4112001_ne_10_030_20220723.tif",  # noqa: E501
    ],
)
def test_naip(href: str) -> None:
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
    if "/ca/2022/ca_060cm" in href:
        # verify that the new item ID includes both area & subarea
        assert item.id == "ca_m_4112001_sw_10_060_20220716"
    if "030cm" in href:
        # verify that the new item ID includes both area & subarea
        assert item.id == "ca_m_4112001_ne_10_030_20220723"
        assert item.common_metadata.gsd == 0.3
