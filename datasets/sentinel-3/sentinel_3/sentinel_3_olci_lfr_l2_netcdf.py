from typing import List, Union

import pystac
from sentinel_3.sentinel_3_base import BaseSentinelCollection

from pctasks.core.models.task import WaitTaskResult
from pctasks.core.storage import StorageFactory

ASSET_DESCRIPTIONS = {
    "safe-manifest": "SAFE product manifest",
    "gifapar": "Green instantaneous Fraction of Absorbed Photosynthetically Active Radiation (FAPAR)",  # noqa
    "ogvi": "OLCI Global Vegetation Index (OGVI)",
    "otci": "OLCI Terrestrial Chlorophyll Index (OTCI)",
    "iwv": "Integrated water vapour column",
    "rcOgvi": "Rectified reflectance",
    "rcGifapar": "Rectified reflectance",
    "lqsf": "Land quality and science flags",
    "timeCoordinates": "Time coordinate annotations",
    "geoCoordinates": "Geo coordinate annotations",
    "tieGeoCoordinates": "Tie-point geo coordinate annotations",
    "tieGeometries": "Tie-point geometry annotations",
    "tieMeteo": "Tie-point meteo annotations",
    "instrumentData": "Instrument annotations",
}


class Collection(BaseSentinelCollection):
    @classmethod
    def create_item(
        cls, asset_uri: str, storage_factory: StorageFactory
    ) -> Union[List[pystac.Item], WaitTaskResult]:
        storage, json_path = storage_factory.get_storage_for_file(asset_uri)
        item_dict = storage.read_json(json_path)

        item_dict = cls.base_updates(item_dict, fix_geometry=True, buffer0=True)
        if item_dict is None:
            # Skip any NT scenes
            return []

        # Grab the shape; we'll move it to assets to be consistent with the
        # other collections
        shape = item_dict["properties"].pop("s3:shape")

        for asset_key, asset in item_dict["assets"].items():
            if "resolution" in asset:
                # flip to row, column order
                asset["s3:resolution"] = asset.pop("resolution")[::-1]
                # add shape, flip to row, column order
                asset["s3:shape"] = shape[::-1]

            # clean up descriptions
            if asset_key in ASSET_DESCRIPTIONS:
                asset["description"] = ASSET_DESCRIPTIONS[asset_key]

        return [pystac.Item.from_dict(item_dict)]
