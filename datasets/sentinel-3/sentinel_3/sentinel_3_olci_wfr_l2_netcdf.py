from pathlib import Path
from typing import List, Union

import pystac

from pctasks.core.models.task import WaitTaskResult
from pctasks.core.storage import StorageFactory
from sentinel_3.sentinel_3_base import BaseSentinelCollection


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

        asset_directory = Path(item_dict["assets"]["safe-manifest"]["href"]).parent.name
        assert asset_directory.endswith(".SEN3")

        # Item id contains unnecessary trailing underscores
        item_dict["id"] = item_dict["id"].rstrip("_")

        # ---- PROPERTIES ----
        properties = item_dict["properties"]

        # ---- ASSETS ----
        assets = item_dict["assets"]
        resolutions = set()

        for v in assets.values():
            # Move description to title
            title = v.pop("description", None)
            if title:
                v["title"] = title

            resolution = v.pop("resolution", None)
            if resolution:
                resolutions.add(tuple(resolution))

        # There is a lonely "resolution" field on the ntc_aod asset that
        # is not part of the STAC spec. This would normally go in "raster:bands",
        # but we are not using that extension. Propose moving this to Item
        # properties under "s3:spatial_resolution", which matches Sentinel-5P.
        assert len(resolutions) == 1, len(resolutions)
        parts = resolutions.pop()
        assert len(parts) == 2, len(parts)
        properties["s3:spatial_resolution"] = list(parts)

        item = pystac.Item.from_dict(item_dict)

        return [item]


if __name__ == "__main__":
    c = Collection()
    asset_uri = "blob://sentinel3euwest/sentinel-3-stac/OLCI/OL_2_WFR___/2023/01/01/S3A_OL_2_WFR_20230101T000030_20230101T000330_0179_094_016_2880.json"  # noqa: E501
    storage_factory = StorageFactory()
    [item] = c.create_item(asset_uri, storage_factory)
    item.validate()

    assert item.id == "S3A_OL_2_WFR_20230101T000030_20230101T000330_0179_094_016_2880"
    assert item.properties["s3:processing_timeliness"] == "NT"
    assert item.properties["start_datetime"] == "2023-01-01T00:00:29.538087Z"
    assert item.properties["s3:product_type"] == "OL_2_WFR___"
    assert item.properties["s3:product_name"] == "WFR"
    for key in [
        "s3:saline_water",
        "s3:coastal",
        "s3:fresh_inland_water",
        "s3:tidal_region",
        "s3:land",
        "s3:cosmetic",
        "s3:duplicated",
        "s3:saturated",
        "s3:dubious_samples",
        "s3:invalid",
    ]:
        assert key in item.properties

    with open("sentinel-3-olci-wfr-l2.json", "w") as f:
        import json

        f.write(json.dumps(item.to_dict(), indent=2))
