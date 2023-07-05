import s1grd
from pctasks.core.storage import StorageFactory


def test_get_item_storage():
    asset_uri = "blob://sentinel1euwest/s1-grd/GRD/2023/6/20/EW/DH/S1A_EW_GRDM_1SDH_20230620T020009_20230620T020113_049063_05E665_5673/manifest.safe"  # noqa: E501
    storage_factory = StorageFactory()
    storage, path = s1grd.get_item_storage(asset_uri, storage_factory=storage_factory)
    assert path == "GRD/2023/6/20/EW/DH/S1A_EW_GRDM_1SDH_20230620T020009_20230620T020113_049063_05E665.json"  # noqa: E501
    assert storage.root_uri == "blob://sentinel1euwest/s1-grd-stac"