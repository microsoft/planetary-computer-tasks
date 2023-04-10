import datetime
import typing

import pystac
import pytest

import pctasks.core.cosmos.containers.items
import pctasks.core.models.item


@pytest.fixture
def stac_item() -> typing.Generator[pystac.Item, None, None]:
    """A simple STAC item for record tests."""
    item = pystac.Item(
        "my-item",
        None,
        None,
        datetime.datetime(2000, 1, 1),
        properties={},
        collection="my-collection",
    )
    yield item


def test_from_item(stac_item: pystac.Item):
    result = pctasks.core.models.item.StacItemRecord.from_item(stac_item)
    assert result.stac_id == "my-collection/my-item"
    assert result.collection_id == "my-collection"
    assert result.item_id == "my-item"
    assert result.get_id() == "my-collection:my-item:None:StacItem"


def test_id_validator(stac_item: pystac.Item):
    stac_item.id = "my/item"
    with pytest.raises(ValueError, match="stac_id must contain"):
        pctasks.core.models.item.StacItemRecord.from_item(stac_item)


def test_get_version(stac_item: pystac.Item):
    stac_item.properties["version"] = "2"
    result = pctasks.core.models.item.StacItemRecord.from_item(stac_item)
    assert result.version == "2"


@pytest.mark.parametrize(
    "version, expected",
    [
        (None, "my-collection:my-item:None:ItemUpdated"),
        ("2", "my-collection:my-item:2:ItemUpdated"),
    ],
)
def test_item_update_record(version, expected):
    record = pctasks.core.models.item.ItemUpdatedRecord(
        stac_id="my-collection/my-item", run_id="test", version=version
    )
    result = record.get_id()
    assert result == expected
