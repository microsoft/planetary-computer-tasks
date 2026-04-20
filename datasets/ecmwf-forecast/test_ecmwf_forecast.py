import pytest
from ecmwf_forecast import EcmwfCollection
from pctasks.core.storage import StorageFactory


@pytest.mark.parametrize(
    "href",
    [
        "blob://ai4edataeuwest/ecmwf/20240314/00z/ifs/0p4-beta/enfo/20240314000000-0h-enfo-ef.grib2",
        "blob://ai4edataeuwest/ecmwf/20240314/00z/ifs/0p25/waef/20240314000000-0h-waef-ef.grib2",
    ],
)
def test_ecmwf(href: str) -> None:
    storage_factory = StorageFactory()
    (item,) = EcmwfCollection.create_item(href, storage_factory)
    assert "ecmwf:resolution" in item.properties
    if "/0p4-beta/" in href:
        assert item.properties["ecmwf:resolution"] == "0.40"
    if "/0p25/" in href:
        assert item.properties["ecmwf:resolution"] == "0.25"


def test_scda() -> None:
    href = "blob://ai4edataeuwest/ecmwf/20230702/06z/0p4-beta/scda/20230702060000-0h-scda-fc.grib2"
    storage_factory = StorageFactory()
    items = EcmwfCollection.create_item(href, storage_factory)
    assert isinstance(items, list)
    items[0].validate()
