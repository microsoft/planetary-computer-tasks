from typing import List, Union

import pystac
from stactools.ecmwf_forecast import stac

from pctasks.core.models.task import WaitTaskResult
from pctasks.core.storage import StorageFactory
from pctasks.dataset.collection import Collection


class EcmwfCollection(Collection):
    @classmethod
    def create_item(
        cls, asset_uri: str, storage_factory: StorageFactory
    ) -> Union[List[pystac.Item], WaitTaskResult]:
        asset_storage, asset_path = storage_factory.get_storage_for_file(asset_uri)
        # Starting March 2024, the ECMWF forecasts data will be available at 0.25 resolution
        resolution = None
        if "0p25" in asset_path.split("/"):
            resolution = "0.25"
        if "0p4-beta" in asset_path.split("/"):
            resolution = "0.40"
        grib2_href = asset_storage.get_url(asset_path)
        index_href = grib2_href.rsplit(".", 1)[0] + ".index"
        item = stac.create_item(
            [grib2_href, index_href], split_by_step=True, resolution=resolution
        )

        return [item]
