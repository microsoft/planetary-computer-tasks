from typing import List, Union

import orjson
from pctasks.core.utils import completely_flatten
# from pctasks.core.pctasks.core.utils import completely_flatten
import pystac

from pystac.extensions.eo import EOExtension
from pystac.extensions.file import FileExtension
from pystac.extensions.projection import ProjectionExtension
from pystac.extensions.raster import RasterExtension
from shapely.geometry import shape
from stactools.core.projection import reproject_geom
from stactools.core.utils.antimeridian import Strategy, fix_item

from pctasks.core.models.task import WaitTaskResult
from pctasks.core.storage import StorageFactory
from pctasks.dataset.collection import Collection
# from pctasks.core.pctasks.core.models.task import WaitTaskResult
# from pctasks.core.pctasks.core.storage import StorageFactory
# from pctasks.dataset.pctasks.dataset.collection import Collection


SENTINEL_1_GRD_COLLECTION_ID = "sentinel-1-grd"

ASSET_INFO = {
    "vv": {
        "title": "VV: vertical transmit, vertical receive",
        "description": (
            "Terrain-corrected gamma naught values of signal transmitted with "
            "vertical polarization and received with vertical polarization "
            "with radiometric terrain correction applied."
        ),
    },
    "vh": {
        "title": "VH: vertical transmit, horizontal receive",
        "description": (
            "Terrain-corrected gamma naught values of signal transmitted with "
            "vertical polarization and received with horizontal polarization "
            "with radiometric terrain correction applied."
        ),
    },
    "hh": {
        "title": "HH: horizontal transmit, horizontal receive",
        "description": (
            "Terrain-corrected gamma naught values of signal transmitted with "
            "horizontal polarization and received with horizontal polarization "
            "with radiometric terrain correction applied."
        ),
    },
    "hv": {
        "title": "HV: horizontal transmit, vertical receive",
        "description": (
            "Terrain-corrected gamma naught values of signal transmitted with "
            "horizontal polarization and received with vertical polarization "
            "with radiometric terrain correction applied."
        ),
    },
}


class S1RTCCollection(Collection):  # type: ignore
    @classmethod
    def create_item(
        cls, asset_uri: str, storage_factory: StorageFactory
    ) -> Union[List[pystac.Item], WaitTaskResult]:

        storage, path = storage_factory.get_storage_for_file(asset_uri)
        item_dict = orjson.loads(storage.read_bytes(path))

        # Remove -rtc from asset keys
        new_assets = {}
        for asset_key, asset in item_dict["assets"].items():
            new_assets[asset_key.replace("-rtc", "")] = asset
        item_dict["assets"] = new_assets

        item = pystac.Item.from_dict(item_dict, preserve_dict=False)

        # Remove providers
        item.properties.pop("providers", None)

        # Avoid non-IW instrument mode items. There was a single EW instrument
        # mode item, avoid it as it was a mistaken process.
        if item.properties["sar:instrument_mode"] != "IW":
            return []

        # Add derived-from link
        item.links.append(
            pystac.Link(
                rel=pystac.RelType.DERIVED_FROM,
                title="Sentinel 1 GRD Item",
                media_type=pystac.MediaType.JSON,
                target=(
                    f"collections/{SENTINEL_1_GRD_COLLECTION_ID}/"
                    f"items/{item.id.replace('_rtc', '')}"
                ),
            )
        )

        # Add missing extension declarations
        ProjectionExtension.add_to(item)
        FileExtension.add_to(item)
        RasterExtension.add_to(item)

        # Remove EO extension
        EOExtension.remove_from(item)

        # Remove eo:bands from assets; fix-up titles and descriptions
        for asset_key, asset in item.assets.items():
            _ = asset.extra_fields.pop("eo:bands", None)
            asset.title = ASSET_INFO[asset_key]["title"]
            asset.description = ASSET_INFO[asset_key]["description"]

        # Reproject if necessary
        assert item.geometry
        needs_reprojection = False
        for coord in completely_flatten(item.geometry["coordinates"]):
            if coord < -180 or coord > 180:
                needs_reprojection = True
                break

        if needs_reprojection:
            epsg = ProjectionExtension.ext(item).epsg
            item.geometry = reproject_geom(f"epsg:{epsg}", "epsg:4326", item.geometry)

            footprint = shape(item.geometry)
            item.bbox = list(footprint.bounds)

        # Fix anti-meridian issues
        fix_item(item, Strategy.NORMALIZE)

        return [item]


if __name__ == "__main__":
    hrefs = [
        # "/Users/pjh/data/sentinel-1/catalyst/S1A_IW_GRDH_1SDH_20230526T072022_20230526T072051_048701_05DB6E_rtc.json",
        # "/Users/pjh/data/sentinel-1/catalyst/S1A_IW_GRDH_1SDV_20141010T035727_20141010T035756_002762_0031AC_rtc.json",
        "/Users/pjh/data/sentinel-1/catalyst/S1A_IW_GRDH_1SDH_20230501T085348_20230501T085417_048338_05D046_rtc.json",
    ]
    for href in hrefs:
        storage_factory = StorageFactory()
        c = S1RTCCollection()
        item = c.create_item(href, storage_factory)[0]
        item.validate()
        import json
        with open(f"{item.id}.json", "w") as f:
            json.dump(item.to_dict(), f, indent=4)