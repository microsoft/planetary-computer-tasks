from typing import List, Union

import pystac
from sentinel_3.sentinel_3_base import BaseSentinelCollection

from pctasks.core.models.task import WaitTaskResult
from pctasks.core.storage import StorageFactory

ASSET_DESCRIPTIONS = {
    "safe-manifest": "SAFE product manifest",
    "l2p": "Skin Sea Surface Temperature (SST) values",
    "eop-metadata": "Metadata produced by the European Organisation for the Exploitation of Meteorological Satellites (EUMETSAT)",  # noqa: E501
    "browse-jpg": "Preview image produced by the European Organisation for the Exploitation of Meteorological Satellites (EUMETSAT)",  # noqa: E501
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
                # resolution is a text string, not a list of numbers
                assert asset["resolution"] == "1 km at nadir"
                asset.pop("resolution")
                asset["s3:resolution"] = [1000, 1000]
                # add shape, flip to row, column order
                asset["s3:shape"] = shape[::-1]

            # clean up descriptions
            if asset_key in ASSET_DESCRIPTIONS:
                asset["description"] = ASSET_DESCRIPTIONS[asset_key]

        return [pystac.Item.from_dict(item_dict)]
