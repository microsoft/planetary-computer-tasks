import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, cast

import pytest

from pctasks.core.utils.summary import (
    DistinctKeySets,
    DistinctValueSummary,
    FloatValueCount,
    KeySet,
    ListValueCount,
    MixedKeySets,
    ObjectListSummary,
    ObjectPropertySummary,
    ObjectSummary,
    StringValueCount,
    SummarySettings,
    ValueTypes,
    make_collection,
)

HERE = Path(__file__).parent
ITEMS_DIR = Path(__file__).parent.parent / "data-files" / "items"
SUMMARIES_DIR = HERE.parent / "data-files" / "summaries"


def test_asset_counts():
    o1 = {
        "assets": {
            "metadata": {
                "href": "md.html",
                "type": "text/plain",
                "roles": ["metadata"],
                "title": "FGDC Metdata",
            }
        }
    }

    o2 = {
        "assets": {
            "fetadata": {
                "href": "md.html",
                "type": "text/plain",
                "roles": ["metadata"],
                "title": "FGDC Feta data",
            }
        }
    }

    o3 = o1

    summary = ObjectSummary.summarize(o1, o2, o3)
    asset_summary = summary.keys["assets"]
    assert isinstance(asset_summary, ObjectPropertySummary)
    assert asset_summary.summary.keys["metadata"].count_with == 2
    assert asset_summary.summary.keys["metadata"].count_without == 1
    assert asset_summary.summary.keys["fetadata"].count_with == 1
    assert asset_summary.summary.keys["fetadata"].count_without == 2


def test_merge_keysets():
    ks1 = DistinctKeySets(
        values=[
            KeySet(keys={"hh-rtc", "hv-rtc"}, count_with=1),
        ]
    )

    ks2 = DistinctKeySets(
        values=[
            KeySet(keys={"vv-rtc", "vh-rtc"}, count_with=1),
        ]
    )

    merged = ks1.merge(ks2, settings=SummarySettings())
    assert isinstance(merged, DistinctKeySets)

    assert len(merged.values) == 2


def test_object_list_merge():
    o1 = {
        "eo:bands": [
            {"name": "Red", "common_name": "red"},
            {"name": "Green", "common_name": "green"},
            {"name": "Blue", "common_name": "blue"},
            {"name": "NIR", "common_name": "nir", "description": "near-infrared"},
        ]
    }

    o2 = {
        "eo:bands": [
            {"name": "Red", "common_name": "red"},
            {"name": "Green", "common_name": "green"},
            {"name": "Blue", "common_name": "blue"},
            {"name": "NIR", "common_name": "nir", "description": "near-infrared"},
        ]
    }

    summary = ObjectSummary.summarize(o1, o2)

    bands_summary = summary.keys["eo:bands"]
    for object_summary in cast(ObjectListSummary, bands_summary).values:
        assert object_summary.count == 2
        assert "common_name" in object_summary.keys
        assert "name" in object_summary.keys


def test_keyset_summary_distinct():
    o1 = {
        "one": 1,
        "two": 2,
    }

    o2 = {
        "two": 2,
        "three": 3,
    }

    o3 = {
        "three": 3,
    }

    summary_1 = ObjectSummary.summarize_dict(o1)
    assert isinstance(summary_1.key_sets, DistinctKeySets)
    assert len(summary_1.key_sets.values) == 1

    summary = ObjectSummary.summarize(o1, o1, o2, o3)
    assert isinstance(summary.key_sets, DistinctKeySets)
    assert len(summary.key_sets.values) == 3


def test_keyset_summary_mixed():
    o1 = {
        1: "one",
        2: "two",
    }

    objs = []
    for i in range(10):
        objs.append({k + i: v for k, v in o1.items()})

    summary = ObjectSummary.summarize(*objs)
    assert isinstance(summary.key_sets, MixedKeySets)


def test_io_lulc():
    item = json.loads((ITEMS_DIR / "io-lulc-item.json").read_text())
    summary = ObjectSummary.summarize_dict(item, include_keys=["properties", "assets"])

    assert (
        cast(
            DistinctValueSummary,
            cast(ObjectPropertySummary, summary.keys["properties"]).summary.keys[
                "label:properties"
            ],
        )
        .values[0]
        .type
        == ValueTypes.NULL
    )


def test_s1_rtc_keysets():
    item1 = json.loads(
        (
            ITEMS_DIR
            / "s1-rtc"
            / "2019/12/15/IW/DH/"
            / "S1A_IW_GRDH_1SDH_20191215T034818"
            "_20191215T034847_030353_0378EA_rtc.json"
        ).read_text()
    )

    item2 = json.loads(
        (
            ITEMS_DIR
            / "s1-rtc"
            / "2019/12/15/IW/DV/"
            / "S1A_IW_GRDH_1SDV_20191215T003835"
            "_20191215T003904_030352_0378DC_rtc.json"
        ).read_text()
    )

    # Remove noise
    for d in [item1, item2]:
        keys = list(d.keys())
        for k in keys:
            if k != "assets":
                d.pop(k)
        for asset in d["assets"].values():
            asset_keys = list(asset.keys())
            for k in asset_keys:
                if k != "href":
                    asset.pop(k)

    summary = ObjectSummary.summarize(
        item1, item2, include_keys=["properties", "assets"]
    )

    asset_summary = summary.keys["assets"]
    assert isinstance(asset_summary, ObjectPropertySummary)
    key_sets = asset_summary.summary.key_sets

    assert isinstance(key_sets, DistinctKeySets)
    assert len(key_sets.values) == 2
    assert key_sets.values[0].keys == {"hh-rtc", "hv-rtc"}
    assert key_sets.values[1].keys == {"vv-rtc", "vh-rtc"}


def test_multilevel_include():
    item1 = json.loads(
        (
            ITEMS_DIR
            / "s1-rtc"
            / "2019/12/15/IW/DH/"
            / "S1A_IW_GRDH_1SDH_20191215T034818"
            "_20191215T034847_030353_0378EA_rtc.json"
        ).read_text()
    )

    item2 = json.loads((ITEMS_DIR / "s1-grd.json").read_text())

    summary = ObjectSummary.summarize(item1, item2, include_keys=["geometry.type"])

    geom_summary = summary.keys["geometry"]
    assert isinstance(geom_summary, ObjectPropertySummary)
    assert len(geom_summary.summary.keys) == 1
    type_summary = geom_summary.summary.keys["type"]
    assert isinstance(type_summary, DistinctValueSummary)
    assert set([v.value for v in type_summary.values]) == {"Polygon", "MultiPolygon"}


def test_single_naip_summary():
    item = json.loads((ITEMS_DIR / "naip" / "naip1.json").read_text())

    summary = ObjectSummary.summarize_dict(item, include_keys=["properties", "assets"])

    # print(summary.json(indent=2))

    assert summary.dict()["keys"]["properties"]["summary"]["keys"]["gsd"] == (
        DistinctValueSummary(
            count_with=1,
            count_without=0,
            values=[FloatValueCount(value=0.6, count=1)],
        ).dict()
    )


def test_two_naip_summary():
    item1 = json.loads((ITEMS_DIR / "naip" / "naip1.json").read_text())
    item2 = json.loads((ITEMS_DIR / "naip" / "naip2.json").read_text())

    summary = ObjectSummary.summarize(
        item1, item2, include_keys=["properties", "assets"]
    )

    # print(summary.json(indent=2))

    assert summary.dict()["keys"]["properties"]["summary"]["keys"]["gsd"] == (
        DistinctValueSummary(
            count_with=2,
            count_without=0,
            values=[FloatValueCount(value=0.6, count=2)],
        ).dict()
    )

    image_summary = summary.dict()["keys"]["assets"]["summary"]["keys"]["image"]

    assert image_summary["summary"]["keys"]["roles"] == (
        DistinctValueSummary(
            count_with=2,
            count_without=0,
            values=[ListValueCount(value=["data"], count=2)],  # type: ignore
        ).dict()
    )

    assert image_summary["summary"]["keys"]["eo:bands"]["values"][0]["keys"][
        "common_name"
    ] == (
        DistinctValueSummary(
            count_with=2,
            count_without=0,
            values=[StringValueCount(value="red", count=2)],
        ).dict()
    )


def test_include_key_three_deep():
    item = json.loads((ITEMS_DIR / "naip" / "naip1.json").read_text())

    summary = ObjectSummary.summarize_dict(item, include_keys=["assets.image.title"])

    print(summary.json(indent=2))

    s = summary.dict()

    assert len(s["keys"]) == 1
    assert len(s["keys"]["assets"]["summary"]["keys"]) == 1
    assert len(s["keys"]["assets"]["summary"]["keys"]["image"]["summary"]["keys"]) == 1

    assert summary.dict()["keys"]["assets"]["summary"]["keys"]["image"]["summary"][
        "keys"
    ]["title"] == (
        DistinctValueSummary(
            count_with=1,
            count_without=0,
            values=[StringValueCount(value="RGBIR COG tile", count=1)],
        ).dict()
    )


def test_several_asset_descriptions():
    item = json.loads((ITEMS_DIR / "naip" / "naip1.json").read_text())

    items: List[Dict[str, Any]] = []
    for i in range(100):
        it = deepcopy(item)
        it["assets"]["image"]["description"] = f"Image {i%20}"
        items.append(it)

    summary = ObjectSummary.summarize(
        *items,
        include_keys=["assets.image.description"],
        settings=SummarySettings(max_distinct_values=20),
    )

    print(summary.json(indent=2))

    assert summary.dict()["keys"]["assets"]["summary"]["keys"]["image"]["summary"][
        "keys"
    ]["description"] == (
        DistinctValueSummary(
            count_with=100,
            count_without=0,
            values=[StringValueCount(value=f"Image {i}", count=5) for i in range(20)],
        ).dict()
    )


@pytest.fixture
def s3_frp_summary():
    p = SUMMARIES_DIR.joinpath("sentinel-3-olci-lfr-l2-netcdf.json")
    return ObjectSummary.parse_file(p)


def test_make_collection(s3_frp_summary):
    percentages = {
        "s3:coastalPixels_percentage",
        "s3:salineWaterPixels_percentage",
        "s3:cosmeticPixels_percentage",
        "s3:dubiousSamples_percentage",
        "s3:freshInlandWaterPixels_percentage",
        "s3:invalidPixels_percentage",
        "s3:landPixels_percentage",
        "s3:duplicatedPixels_percentage",
        "s3:tidalRegionPixels_percentage",
        "s3:saturatedPixels_percentage",
        "sat:absolute_orbit",
        "sat:relative_orbit",
        "eo:cloud_cover",
    }
    result = make_collection(
        s3_frp_summary,
        "id",
        title="Sentinel 3",
        extra_fields={
            "msft:region": "westeurope",
        },
        extra_summary_exclude={
            "s3:shape",
            "s3:gsd",
            "s3:productType",
            "sat:orbit_state",
            "s3:mode",
            "providers",
        }
        | percentages,
        item_assets_exclude="resolution",
    )

    expected = {
        "stac_version": "1.0.0",
        "id": "id",
        "type": "Collection",
        "description": "{{ collection.description }}",
        "title": "Sentinel 3",
        "keywords": [],
        "stac_extensions": [],
        "links": [],
        "msft:region": "westeurope",
        "summaries": {
            "platform": ["Sentinel-3A", "Sentinel-3B"],
            "constellation": ["Sentinel-3"],
            "instruments": [["OLCI"]],
            "sat:platform_international_designator": ["2016-011A", "2018-039A"],
        },
        "item_assets": {
            "safe-manifest": {"type": "application/xml", "roles": ["metadata"]},
            "ogvi": {
                "description": "OLCI global Vegetal Index",
                "type": "application/x-netcdf",
                "roles": ["data"],
                "eo:bands": [
                    {
                        "name": "Oa03",
                        "description": "Band 3 - Chlorophyll absorption maximum, biogeochemistry, vegetation",
                        "center_wavelength": 442.5,
                        "band_width": 10,
                    },
                    {
                        "name": "Oa10",
                        "description": "Band 10 - Chlorophyll fluorescence peak, red edge",
                        "center_wavelength": 681.25,
                        "band_width": 7.5,
                    },
                    {
                        "name": "Oa17",
                        "description": "Band 17 - Atmospheric / aerosol correction, clouds, pixel co-registration",
                        "center_wavelength": 865,
                        "band_width": 20,
                    },
                ],
            },
            "otci": {
                "description": "OLCI Terrestrial Chlorophyll Index",
                "type": "application/x-netcdf",
                "roles": ["data"],
                "eo:bands": [
                    {
                        "name": "Oa10",
                        "description": "Band 10 - Chlorophyll fluorescence peak, red edge",
                        "center_wavelength": 681.25,
                        "band_width": 7.5,
                    },
                    {
                        "name": "Oa11",
                        "description": "Band 11 - Chlorophyll fluorescence baseline, red edge transition",
                        "center_wavelength": 708.75,
                        "band_width": 10,
                    },
                    {
                        "name": "Oa12",
                        "description": "Band 12 - O2 absorption / clouds, vegetation",
                        "center_wavelength": 753.75,
                        "band_width": 7.5,
                    },
                ],
            },
            "iwv": {
                "description": "Integrated water vapour column",
                "type": "application/x-netcdf",
                "roles": ["data"],
                "eo:bands": [
                    {
                        "name": "Oa18",
                        "description": "Band 18 - Water vapour absorption reference. Common reference band with SLSTR. Vegetation monitoring",
                        "center_wavelength": 885,
                        "band_width": 10,
                    },
                    {
                        "name": "Oa19",
                        "description": "Band 19 - Water vapour absorption, vegetation monitoring (maximum REFLECTANCE)",
                        "center_wavelength": 900,
                        "band_width": 10,
                    },
                ],
            },
            "rcOgvi": {
                "description": "Rectified Reflectance",
                "type": "application/x-netcdf",
                "roles": ["data"],
                "eo:bands": [
                    {
                        "name": "Oa10",
                        "description": "Band 10 - Chlorophyll fluorescence peak, red edge",
                        "center_wavelength": 681.25,
                        "band_width": 7.5,
                    },
                    {
                        "name": "Oa17",
                        "description": "Band 17 - Atmospheric / aerosol correction, clouds, pixel co-registration",
                        "center_wavelength": 865,
                        "band_width": 20,
                    },
                ],
            },
            "lqsf": {
                "description": "Land Quality and Science Flags",
                "type": "application/x-netcdf",
                "roles": ["data"],
            },
            "timeCoordinates": {
                "description": "Time Coordinates Annotations",
                "type": "application/x-netcdf",
                "roles": ["data"],
            },
            "geoCoordinates": {
                "description": "Geo Coordinates Annotations",
                "type": "application/x-netcdf",
                "roles": ["data"],
            },
            "tieGeoCoordinates": {
                "description": "Tie-Point Geo Coordinate Annotations",
                "type": "application/x-netcdf",
                "roles": ["data"],
            },
            "tieGeometries": {
                "description": "Tie-Point Geometries Annotations",
                "type": "application/x-netcdf",
                "roles": ["data"],
            },
            "tieMeteo": {
                "description": "Tie-Point Meteo Annotations",
                "type": "application/x-netcdf",
                "roles": ["data"],
            },
            "instrumentData": {
                "description": "Instrument Annotation",
                "type": "application/x-netcdf",
                "roles": ["data"],
            },
            "gifapar": {
                "description": "Green Instantaneous FAPAR",
                "type": "application/x-netcdf",
                "roles": ["data"],
                "eo:bands": [
                    {
                        "name": "Oa03",
                        "description": "Band 3 - Chlorophyll absorption maximum, biogeochemistry, vegetation",
                        "center_wavelength": 442.5,
                        "band_width": 10,
                    },
                    {
                        "name": "Oa10",
                        "description": "Band 10 - Chlorophyll fluorescence peak, red edge",
                        "center_wavelength": 681.25,
                        "band_width": 7.5,
                    },
                    {
                        "name": "Oa17",
                        "description": "Band 17 - Atmospheric / aerosol correction, clouds, pixel co-registration",
                        "center_wavelength": 865,
                        "band_width": 20,
                    },
                ],
            },
            "rcGifapar": {
                "description": "Rectified Reflectance",
                "type": "application/x-netcdf",
                "roles": ["data"],
            },
        },
    }
    assert result == expected
    assert 0
