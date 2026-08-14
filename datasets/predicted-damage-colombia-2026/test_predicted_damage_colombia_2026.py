from datetime import datetime, timezone

import pytest
from predicted_damage_colombia_2026 import PredictedDamageColombia2026

from pctasks.core.storage import StorageFactory

CALI = (
    "blob://ai4edataeuwest/ai4good/colombia2026/cali/2026-08-10/"
    "airbus_cali_warped_cog_model-predictions.tif"
)
PEREIRA = (
    "blob://ai4edataeuwest/ai4good/colombia2026/pereira/2026-08-12/"
    "vantor_8-12_pereira_model-predictions.tif"
)

ASSET_KEYS = {"visual", "valid-area-mask", "overture-buildings", "google-buildings"}


@pytest.mark.parametrize(
    "href,expected_id,expected_datetime,expected_bbox",
    [
        (
            CALI,
            "cali-2026-08-10",
            datetime(2026, 8, 10, tzinfo=timezone.utc),
            [-76.6146, 3.4127, -76.4588, 3.5479],
        ),
        (
            PEREIRA,
            "pereira-2026-08-12",
            datetime(2026, 8, 12, tzinfo=timezone.utc),
            [-75.7856, 4.7758, -75.6922, 4.8433],
        ),
    ],
)
def test_create_item(
    href: str,
    expected_id: str,
    expected_datetime: datetime,
    expected_bbox: list,
) -> None:
    (item,) = PredictedDamageColombia2026.create_item(href, StorageFactory())
    item.validate()

    assert item.id == expected_id
    assert item.datetime == expected_datetime
    assert set(item.assets) == ASSET_KEYS
    assert item.bbox == pytest.approx(expected_bbox, abs=1e-4)
    assert item.geometry["type"] == "Polygon"


@pytest.mark.parametrize("href", [CALI, PEREIRA])
def test_asset_media_types(href: str) -> None:
    (item,) = PredictedDamageColombia2026.create_item(href, StorageFactory())

    assert item.assets["visual"].media_type == (
        "image/tiff; application=geotiff; profile=cloud-optimized"
    )
    assert item.assets["valid-area-mask"].media_type == "application/geo+json"
    for key in ["overture-buildings", "google-buildings"]:
        asset = item.assets[key]
        assert asset.media_type == "application/geopackage+sqlite3"
        assert asset.extra_fields["table:storage_options"] == {
            "account_name": "ai4edataeuwest"
        }


@pytest.mark.parametrize(
    "href,expected_google_file",
    [
        (
            CALI,
            "airbus_8-10_cali_hdx_building_footprints_with_predictions_validated.gpkg",
        ),
        (PEREIRA, "vantor_8-12_pereira_google_buildings_with_predictions.gpkg"),
    ],
)
def test_google_buildings_naming_varies_by_area(
    href: str, expected_google_file: str
) -> None:
    (item,) = PredictedDamageColombia2026.create_item(href, StorageFactory())

    assert item.assets["google-buildings"].href.endswith(expected_google_file)
    assert "overture" in item.assets["overture-buildings"].href


def test_missing_assets_raises() -> None:
    href = (
        "blob://ai4edataeuwest/ai4good/colombia2026/nowhere/2026-08-12/"
        "x_model-predictions.tif"
    )
    with pytest.raises(ValueError, match="Expected exactly one file matching"):
        PredictedDamageColombia2026.create_item(href, StorageFactory())


def test_non_date_folder_raises() -> None:
    href = (
        "blob://ai4edataeuwest/ai4good/colombia2026/cali/not-a-date/"
        "x_model-predictions.tif"
    )
    with pytest.raises(ValueError, match="Expected an <area>/<YYYY-MM-DD> path"):
        PredictedDamageColombia2026.create_item(href, StorageFactory())
