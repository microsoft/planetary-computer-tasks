import posixpath
import re
from datetime import datetime, timezone
from typing import Any, Dict, Iterator, List, Tuple, Union

import pystac

from pctasks.core.models.task import WaitTaskResult
from pctasks.core.storage import Storage, StorageFactory
from pctasks.dataset.collection import Collection

# Assets are organized as colombia2026/<area>/<YYYY-MM-DD>/<files>, one item per
# area/date folder.
GPKG_MEDIA_TYPE = "application/geopackage+sqlite3"
TABLE_EXTENSION = "https://stac-extensions.github.io/table/v1.2.0/schema.json"
STORAGE_OPTIONS = {"account_name": "ai4edataeuwest"}

MASK_MATCH = "valid_area_mask"

GPKG_ASSETS: Dict[str, Dict[str, Any]] = {
    "overture-buildings": {
        "match": ["overture"],
        "title": "Overture Maps building damage footprints",
        "description": (
            "GeoPackage of Overture Maps building footprints with predicted "
            "earthquake damage."
        ),
    },
    "google-buildings": {
        # Cali labels these "hdx"; later areas label them "google".
        "match": ["google", "hdx"],
        "title": "Google building damage footprints",
        "description": (
            "GeoPackage of Google building footprints with predicted earthquake damage."
        ),
    },
}


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def _bbox_geometry(bbox: List[float]) -> Dict[str, Any]:
    xmin, ymin, xmax, ymax = bbox
    return {
        "type": "Polygon",
        "coordinates": [
            [
                [xmin, ymin],
                [xmax, ymin],
                [xmax, ymax],
                [xmin, ymax],
                [xmin, ymin],
            ]
        ],
    }


def _positions(coordinates: Any) -> Iterator[Tuple[float, float]]:
    if coordinates and isinstance(coordinates[0], (int, float)):
        yield (coordinates[0], coordinates[1])
    else:
        for part in coordinates:
            yield from _positions(part)


def _mask_extent(
    storage: Storage, mask_path: str
) -> Tuple[Dict[str, Any], List[float]]:
    mask = storage.read_json(mask_path)
    geometries = [f.get("geometry", f) for f in mask.get("features", [mask])]

    positions = [p for g in geometries for p in _positions(g["coordinates"])]
    xs = [p[0] for p in positions]
    ys = [p[1] for p in positions]
    bbox = [min(xs), min(ys), max(xs), max(ys)]

    if len(geometries) == 1:
        return geometries[0], bbox
    return _bbox_geometry(bbox), bbox


def _find_one(paths: List[str], matches: List[str], folder: str) -> str:
    found = [
        p for p in paths if any(m in posixpath.basename(p).lower() for m in matches)
    ]
    if len(found) != 1:
        raise ValueError(
            f"Expected exactly one file matching {matches} in {folder}, found {found}"
        )
    return found[0]


class PredictedDamageColombia2026(Collection):
    @classmethod
    def create_item(
        cls, asset_uri: str, storage_factory: StorageFactory
    ) -> Union[List[pystac.Item], WaitTaskResult]:
        storage, tif_path = storage_factory.get_storage_for_file(asset_uri)

        folder = posixpath.dirname(tif_path)
        date_str = posixpath.basename(folder)
        area = _slug(posixpath.basename(posixpath.dirname(folder)))
        try:
            item_datetime = datetime.strptime(date_str, "%Y-%m-%d").replace(
                tzinfo=timezone.utc
            )
        except ValueError:
            raise ValueError(
                f"Expected an <area>/<YYYY-MM-DD> path for asset {asset_uri}"
            )
        if not area:
            raise ValueError(f"Expected an <area>/<YYYY-MM-DD> path for {asset_uri}")

        sibling_paths = list(storage.list_files(name_starts_with=f"{folder}/"))
        gpkg_paths = [p for p in sibling_paths if p.lower().endswith(".gpkg")]

        mask_path = _find_one(sibling_paths, [MASK_MATCH], folder)
        geometry, bbox = _mask_extent(storage, mask_path)

        item = pystac.Item(
            id=f"{area}-{date_str}",
            geometry=geometry,
            bbox=bbox,
            datetime=item_datetime,
            properties={},
            stac_extensions=[TABLE_EXTENSION],
        )

        item.add_asset(
            "visual",
            pystac.Asset(
                href=storage.get_url(tif_path),
                media_type=pystac.MediaType.COG,
                title="Model prediction imagery",
                description=(
                    "Cloud-optimized GeoTIFF of the post-event imagery that the "
                    "damage model was run on."
                ),
                roles=["data", "visual"],
            ),
        )
        item.add_asset(
            "valid-area-mask",
            pystac.Asset(
                href=storage.get_url(mask_path),
                media_type=pystac.MediaType.GEOJSON,
                title="Valid area mask",
                description=(
                    "GeoJSON mask delineating the area covered by the damage "
                    "assessment."
                ),
                roles=["metadata"],
            ),
        )

        for key, info in GPKG_ASSETS.items():
            gpkg_path = _find_one(gpkg_paths, info["match"], folder)
            item.add_asset(
                key,
                pystac.Asset(
                    href=storage.get_url(gpkg_path),
                    media_type=GPKG_MEDIA_TYPE,
                    title=info["title"],
                    description=info["description"],
                    roles=["data"],
                    extra_fields={"table:storage_options": STORAGE_OPTIONS},
                ),
            )

        return [item]
