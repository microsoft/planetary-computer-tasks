from naip import NAIPCollection
from pctasks.core.storage import StorageFactory


def test_naip():
    storage_factory = StorageFactory()
    (item,) = NAIPCollection.create_item(
        "blob://naipeuwest/naip/v002/wa/2021/wa_060cm_2021/45116/m_4511601_ne_11_060_20210629.tif",
        storage_factory,
    )
    item.validate()
    assert "grid:code" not in item.properties
    assert "raster:bands" not in item.assets["image"].extra_fields
    assert item.stac_extensions == [
        "https://stac-extensions.github.io/eo/v1.0.0/schema.json",
        "https://stac-extensions.github.io/projection/v1.0.0/schema.json",
    ]
