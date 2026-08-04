from pystac import Item
import hls2
import pytest
from pctasks.core.storage import StorageFactory

test_storage_account = "hls2euwest"
test_container = "hls2"

@pytest.mark.parametrize(
    "asset_uri",
    [
        f"blob://{test_storage_account}/{test_container}/L30/05/U/LB/2025/02/26/HLS.L30.T05ULB.2025057T212139.v2.0/HLS.L30.T05ULB.2025057T212139.v2.0_stac.json"
    ],
)
def test_hls2_landsat(asset_uri: str) -> None:
    result = hls2.HLS2Collection.create_item(asset_uri, StorageFactory(), upload=False)
    assert result
    item, = result
    assert isinstance(item, Item)
    assert item.assets["B01"].href == f'https://{test_storage_account}.blob.core.windows.net/{test_container}/L30/05/U/LB/2025/02/26/HLS.L30.T05ULB.2025057T212139.v2.0/HLS.L30.T05ULB.2025057T212139.v2.0.B01.tif'  # noqa: E501
    assert len(item.stac_extensions) == 4
    assert item.properties["platform"] == "landsat-9"
    assert len(item.assets) == 16
    assert "thumbnail" in item.assets
    item.validate()

@pytest.mark.parametrize(
    "asset_uri",
    [
        f"blob://{test_storage_account}/{test_container}/S30/05/M/KR/2025/01/05/HLS.S30.T05MKR.2025005T204621.v2.0/HLS.S30.T05MKR.2025005T204621.v2.0_stac.json"
    ],
)
def test_hls2_sentinel(asset_uri: str) -> None:
    result = hls2.HLS2Collection.create_item(asset_uri, StorageFactory(), upload=False)
    assert result
    item, = result
    assert isinstance(item, Item)
    assert item
    assert item.assets["B01"].href == f'https://{test_storage_account}.blob.core.windows.net/{test_container}/S30/05/M/KR/2025/01/05/HLS.S30.T05MKR.2025005T204621.v2.0/HLS.S30.T05MKR.2025005T204621.v2.0.B01.tif'  # noqa: E501
    assert len(item.stac_extensions) == 4
    assert item.properties["platform"] == "sentinel-2a"
    assert len(item.assets) == 19 # 18 bands and 1 thumbnail
    assert "thumbnail" in item.assets
    item.validate()


@pytest.mark.parametrize(
    "asset_uri",
    [
        f"blob://{test_storage_account}/{test_container}/S30/06/W/XC/2026/08/01/HLS.S30.T06WXC.2026213T212519.v2.0/HLS.S30.T06WXC.2026213T212519.v2.0_stac.json"
    ],
)
def test_hls2_sentinel_without_browse_image(asset_uri: str) -> None:
    """LP DAAC stopped publishing the .jpg browse image for HLSS30 around 2026-06-17."""
    result = hls2.HLS2Collection.create_item(asset_uri, StorageFactory(), upload=False)
    assert result
    item, = result
    assert isinstance(item, Item)
    assert item.properties["platform"].startswith("sentinel-2")
    assert len(item.assets) == 18 # 18 bands, no thumbnail
    assert "thumbnail" not in item.assets
    item.validate()