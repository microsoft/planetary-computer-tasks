from typing import List, Union

import pystac
from sentinel_3.sentinel_3_base import BaseSentinelCollection

from pctasks.core.models.task import WaitTaskResult
from pctasks.core.storage import StorageFactory

ASSET_DESCRIPTIONS = {
    "safe-manifest": "SAFE product manifest",
    "standard-measurement": "Standard measurement data file",
    "enhanced-measurement": "Enhanced measurement data file",
    "reduced-measurement": "Reduced measurement data file",
    "eop-metadata": "Product metadata file produced by the European Organisation for the Exploitation of Meteorological Satellites (EUMETSAT)",  # noqa
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

        for asset_key, asset in item_dict["assets"].items():
            if "shape" in asset:
                # Shape is a list of single entry dicts containing the length
                # of a series of 1D variables. Removing since we can't format
                # to match the other collections, which are a single 2D list for
                # the primary 2D variable.
                asset.pop("shape")

            # clean up descriptions
            if asset_key in ASSET_DESCRIPTIONS:
                asset["description"] = ASSET_DESCRIPTIONS[asset_key]

        # eo extension is not used
        item_dict["stac_extensions"] = [
            ext for ext in item_dict["stac_extensions"] if "/eo/" not in ext
        ]

        return [pystac.Item.from_dict(item_dict)]
