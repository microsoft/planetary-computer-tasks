from typing import List, Union

import pystac
from sentinel_3.sentinel_3_base import BaseSentinelCollection

from pctasks.core.models.task import WaitTaskResult
from pctasks.core.storage import StorageFactory


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

        # Grab the custom shape field and place on the assets for consistency
        # with the other sentinel-3 collections
        s3_shape = item_dict["properties"].pop("s3:shape")

        for asset_key, asset in item_dict["assets"].items():
            if asset_key == "NTC_AOD":
                # Place the custom shape field on the asset. Reverse the order
                # to be in [row, column] order.
                asset["s3:shape"] = s3_shape[::-1]

                # Reverse the provided resolution order to match the shape order
                asset["s3:spatial_resolution"] = asset.pop("resolution")[::-1]

        return [pystac.Item.from_dict(item_dict)]
