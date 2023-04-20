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

        item_dict = cls.base_updates(item_dict, fix_geometry=True, buffer0=True)
        if item_dict is None:
            return []

        for asset in item_dict["assets"].values():
            # standardize the shape property
            if "syn:shape" in asset:
                assert "resolution" in asset
                shape = asset.pop("syn:shape")
                resolution = asset.pop("resolution")

                if len(shape) == 1:
                    asset["s3:shape"] = [list(shape[0].values())[0]]
                else:
                    columns = next(
                        (d["columns"] for d in shape if "columns" in d), False
                    )
                    rows = next((d["rows"] for d in shape if "rows" in d), False)
                    # "removed pixels" are a columnar dimension.
                    removed_pixels = next(
                        (d["removed_pixels"] for d in shape if "removed_pixels" in d),
                        False,
                    )
                    assert not (columns and removed_pixels)
                    # Use [row, column] order to align with the ordering
                    # provided in the netcdf descriptions and the order used by
                    # xarray, numpy, and rasterio.
                    asset["s3:shape"] = [rows, columns or removed_pixels]

                # Reverse the provided resolution order to match the shape order
                asset["s3:spatial_resolution"] = resolution[::-1]

        return [pystac.Item.from_dict(item_dict)]
