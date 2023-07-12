import pathlib
import pystac

import s1grd
from pctasks.core.storage import StorageFactory


HERE = pathlib.Path(__file__).parent


def test_get_item_storage():
    asset_uri = "blob://sentinel1euwest/s1-grd/GRD/2023/6/20/EW/DH/S1A_EW_GRDM_1SDH_20230620T020009_20230620T020113_049063_05E665_5673/manifest.safe"  # noqa: E501
    storage_factory = StorageFactory()
    storage, path = s1grd.get_item_storage(asset_uri, storage_factory=storage_factory)
    assert (
        path
        == "GRD/2023/6/20/EW/DH/S1A_EW_GRDM_1SDH_20230620T020009_20230620T020113_049063_05E665.json"
    )  # noqa: E501
    assert storage.root_uri == "blob://sentinel1euwest/s1-grd-stac"


def test_rewrite_asset_hrefs():
    archive_storage = StorageFactory().get_storage(
        "blob://sentinel1euwest/s1-grd/GRD/2023/6/28/IW/DV/S1A_IW_GRDH_1SDV_20230628T210705_20230628T210730_049191_05EA4D_21D1"  # noqa: E501
    )

    item = pystac.Item.from_file(str(HERE / "test-data/sentinel-1-grd-item-raw.json"))
    result = {
        k: v.href
        for k, v in s1grd.rewrite_asset_hrefs(
            item,
            archive_storage,
            "/tmp/tmpsskmzq08/S1A_IW_GRDH_1SDV_20230628T210705_20230628T210730_049191_05EA4D_21D1",
        ).assets.items()
    }

    expected = {
        "safe-manifest": "https://sentinel1euwest.blob.core.windows.net/s1-grd/GRD/2023/6/28/IW/DV/S1A_IW_GRDH_1SDV_20230628T210705_20230628T210730_049191_05EA4D_21D1/manifest.safe",
        "schema-product-vh": "https://sentinel1euwest.blob.core.windows.net/s1-grd/GRD/2023/6/28/IW/DV/S1A_IW_GRDH_1SDV_20230628T210705_20230628T210730_049191_05EA4D_21D1/rfi-iw-vh.xml",
        "schema-product-vv": "https://sentinel1euwest.blob.core.windows.net/s1-grd/GRD/2023/6/28/IW/DV/S1A_IW_GRDH_1SDV_20230628T210705_20230628T210730_049191_05EA4D_21D1/annotation/rfi/rfi-iw-vv.xml",
        "schema-calibration-vh": "https://sentinel1euwest.blob.core.windows.net/s1-grd/GRD/2023/6/28/IW/DV/S1A_IW_GRDH_1SDV_20230628T210705_20230628T210730_049191_05EA4D_21D1/annotation/calibration/calibration-iw-vh.xml",
        "schema-calibration-vv": "https://sentinel1euwest.blob.core.windows.net/s1-grd/GRD/2023/6/28/IW/DV/S1A_IW_GRDH_1SDV_20230628T210705_20230628T210730_049191_05EA4D_21D1/annotation/calibration/calibration-iw-vv.xml",
        "schema-noise-vh": "https://sentinel1euwest.blob.core.windows.net/s1-grd/GRD/2023/6/28/IW/DV/S1A_IW_GRDH_1SDV_20230628T210705_20230628T210730_049191_05EA4D_21D1/annotation/calibration/noise-iw-vh.xml",
        "schema-noise-vv": "https://sentinel1euwest.blob.core.windows.net/s1-grd/GRD/2023/6/28/IW/DV/S1A_IW_GRDH_1SDV_20230628T210705_20230628T210730_049191_05EA4D_21D1/annotation/calibration/noise-iw-vv.xml",
        "thumbnail": "https://sentinel1euwest.blob.core.windows.net/s1-grd/GRD/2023/6/28/IW/DV/S1A_IW_GRDH_1SDV_20230628T210705_20230628T210730_049191_05EA4D_21D1/preview/quick-look.png",
        "vh": "https://sentinel1euwest.blob.core.windows.net/s1-grd/GRD/2023/6/28/IW/DV/S1A_IW_GRDH_1SDV_20230628T210705_20230628T210730_049191_05EA4D_21D1/measurement/iw-vh.tiff",
        "vv": "https://sentinel1euwest.blob.core.windows.net/s1-grd/GRD/2023/6/28/IW/DV/S1A_IW_GRDH_1SDV_20230628T210705_20230628T210730_049191_05EA4D_21D1/measurement/iw-vv.tiff",
    }
    assert result == expected
