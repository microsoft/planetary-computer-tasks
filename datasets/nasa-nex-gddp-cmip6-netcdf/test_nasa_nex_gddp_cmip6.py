from pctasks.core.storage import StorageFactory

import nasa_nex_gddp_cmip6


def test_create_item():
    asset_uri = (
        "blob://nasagddp/nex-gddp-cmip6/NEX/GDDP-CMIP6/ACCESS-CM2/historical/r1i1p1f1"
    )
    nasa_nex_gddp_cmip6.NASANEXGDDPCMIP6Collection.limit = 1

    items = nasa_nex_gddp_cmip6.NASANEXGDDPCMIP6Collection.create_item(asset_uri, StorageFactory())
    item = items[0]

    assert set(item.assets) == {
        "hurs",
        "huss",
        "pr",
        "rlds",
        "rsds",
        "sfcWind",
        "tas",
        "tasmax",
        "tasmin",
    }
    assert (
        item.assets["hurs"].href
        == "https://nasagddp.blob.core.windows.net/nex-gddp-cmip6/NEX/GDDP-CMIP6/ACCESS-CM2/historical/r1i1p1f1/hurs/hurs_day_ACCESS-CM2_historical_r1i1p1f1_gn_1950_v1.1.nc"
    )  # noqa: E501
