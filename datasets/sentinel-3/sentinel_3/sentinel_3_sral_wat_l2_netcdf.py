from typing import List, Union

import pystac
from sentinel_3.sentinel_3_base import BaseSentinelCollection

from pctasks.core.models.task import WaitTaskResult
from pctasks.core.storage import StorageFactory

ASSET_DESCRIPTIONS = {
    "safe-manifest": "SAFE product manifest",
    "standardMeasurement": "Standard measurement data file",
    "enhancedMeasurement": "Enhanced measurement data file",
    "reducedMeasurement": "Reduced measurement data file",
    "eopmetadata": "Product metadata file produced by EUMETSAT",
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
            return []

        # Item id contains unnecessary trailing underscores
        item_dict["id"] = item_dict["id"].rstrip("_")

        for asset_key, asset in item_dict["assets"].items():
            if "shape" in asset:
                # Shape is a list of single entry dicts containing the length
                # of a series of 1D variables. Removing since we can't format
                # to match the other collections, which are a single 2D list for
                # the primary 2D variable.
                asset.pop("shape")

            # update descriptions
            asset["description"] = ASSET_DESCRIPTIONS[asset_key]

            # the eopmetadata asset title is not useful
            if asset_key == "eopmetadata":
                asset.pop("title")

        # eo extension is not used
        item_dict["stac_extensions"] = [
            ext for ext in item_dict["stac_extensions"] if "/eo/" not in ext
        ]

        return [pystac.Item.from_dict(item_dict)]
