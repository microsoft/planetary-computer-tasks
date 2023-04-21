# sentinel_3 might not be on your path. Run with
#     PYTHONPATH=datasets/sentinel-3 python -m pytest datasets/sentinel-3/tests/
from sentinel_3 import sentinel_3_olci_lfr_l2_netcdf, sentinel_3_olci_wfr_l2_netcdf
from pctasks.core.storage import StorageFactory


S3_KEYS = {
    "s3:saline_water",
    "s3:coastal",
    "s3:fresh_inland_water",
    "s3:tidal_region",
    "s3:land",
    "s3:cosmetic",
    "s3:duplicated",
    "s3:saturated",
    "s3:dubious_samples",
    "s3:invalid",
}


def test_olci_lfr():
    c = sentinel_3_olci_lfr_l2_netcdf.Collection()
    asset_uri = "blob://sentinel3euwest/sentinel-3-stac/OLCI/OL_2_LFR___/2023/04/01/S3A_OL_2_LFR_20230401T004527_20230401T004655_0088_097_145_1440.json"  # noqa: E501
    storage_factory = StorageFactory()
    [item] = c.create_item(asset_uri, storage_factory)
    item.validate()

    assert item.id == "S3A_OL_2_LFR_20230401T004527_20230401T004655_0088_097_145_1440"
    assert item.properties["s3:processing_timeliness"] == "NT"
    assert item.properties["start_datetime"] == "2023-04-01T00:45:26.790564Z"
    assert item.properties["s3:product_type"] == "OL_2_LFR___"
    assert item.properties["s3:product_name"] == "LFR"

    assert S3_KEYS <= set(item.properties.keys())


def test_olci_wfr():
    c = sentinel_3_olci_wfr_l2_netcdf.Collection()
    asset_uri = "blob://sentinel3euwest/sentinel-3-stac/OLCI/OL_2_WFR___/2023/01/01/S3A_OL_2_WFR_20230101T000030_20230101T000330_0179_094_016_2880.json"  # noqa: E501
    storage_factory = StorageFactory()
    [item] = c.create_item(asset_uri, storage_factory)
    item.validate()

    assert item.id == "S3A_OL_2_WFR_20230101T000030_20230101T000330_0179_094_016_2880"
    assert item.properties["s3:processing_timeliness"] == "NT"
    assert item.properties["start_datetime"] == "2023-01-01T00:00:29.538087Z"
    assert item.properties["s3:product_type"] == "OL_2_WFR___"
    assert item.properties["s3:product_name"] == "WFR"
    assert S3_KEYS <= set(item.properties.keys())
