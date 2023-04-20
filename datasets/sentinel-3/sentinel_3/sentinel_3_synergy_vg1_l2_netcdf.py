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

        # Item id contains unnecessary trailing underscores
        item_dict["id"] = item_dict["id"].rstrip("_")

        for asset in item_dict["assets"].values():
            # standardize the shape property
            if "vg1:shape" in asset:
                assert "resolution" in asset
                shape = asset.pop("vg1:shape")
                resolution = asset.pop("resolution")

                latitude = next((d["latitude"] for d in shape if "latitude" in d))
                longitude = next((d["longitude"] for d in shape if "longitude" in d))
                # Use [row, column] order to align with the ordering
                # provided in the netcdf descriptions and the order used by
                # xarray, numpy, and rasterio.
                asset["s3:shape"] = [latitude, longitude]

                # Reverse the provided resolution order to match the shape order
                asset["s3:spatial_resolution"] = resolution[::-1]

        return [pystac.Item.from_dict(item_dict)]
