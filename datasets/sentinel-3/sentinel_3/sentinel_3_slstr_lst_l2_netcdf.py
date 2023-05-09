from typing import List, Union

import pystac
from sentinel_3.sentinel_3_base import BaseSentinelCollection

from pctasks.core.models.task import WaitTaskResult
from pctasks.core.storage import StorageFactory

ASSET_DESCRIPTIONS = {
    "safe-manifest": "SAFE product manifest",
    "lst-in": "Land Surface Temperature (LST) values",
    "st-ancillary-ds": "LST ancillary measurement dataset",
    "slstr-flags-in": "Global flags for the 1km TIR grid, nadir view",
    "slstr-indices-in": "Scan, pixel and detector indices annotations for the 1km TIR grid, nadir view",  # noqa: E501
    "slstr-time-in": "Time annotations for the 1km grid",
    "slstr-geodetic-in": "Full resolution geodetic coordinates for the 1km TIR grid, nadir view",
    "slstr-cartesian-in": "Full resolution cartesian coordinates for the 1km TIR grid, nadir view",
    "slstr-geometry-tn": "16km solar and satellite geometry annotations, nadir view",
    "slstr-geodetic-tx": "16km geodetic coordinates",
    "slstr-cartesian-tx": "16km cartesian coordinates",
    "slstr-met-tx": "Meteorological parameters regridded onto the 16km tie points",
}


class Collection(BaseSentinelCollection):
    @classmethod
    def create_item(
        cls, asset_uri: str, storage_factory: StorageFactory
    ) -> Union[List[pystac.Item], WaitTaskResult]:

        storage, json_path = storage_factory.get_storage_for_file(asset_uri)
        item_dict = storage.read_json(json_path)

        item_dict = cls.base_updates(item_dict)
        if item_dict is None:
            return []

        # Grab the shape; we'll move it to assets to be consistent with the
        # other collections
        shape = item_dict["properties"].pop("s3:shape")

        for asset_key, asset in item_dict["assets"].items():
            if "resolution" in asset:
                # flip to row, column order
                asset["s3:spatial_resolution"] = asset.pop("resolution")[::-1]
                # add shape, flip to row, column order
                asset["s3:shape"] = shape[::-1]

            # clean up descriptions
            if asset_key in ASSET_DESCRIPTIONS:
                asset["description"] = ASSET_DESCRIPTIONS[asset_key]

        return [pystac.Item.from_dict(item_dict)]
