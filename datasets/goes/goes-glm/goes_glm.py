import sys
import logging
import time
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import List, Union

import pystac
from stactools.goes_glm import stac
from stactools.goes_glm.constants import DATACUBE_EXTENSION

from pctasks.core.models.task import WaitTaskResult
from pctasks.core.storage import StorageFactory
from pctasks.dataset.collection import Collection

GEOPARQUET_CONTAINER = "blob://goeseuwest/noaa-goes-geoparquet/"

# The original GOES ETL code indicates duplicate assets. Is there a way to
# handle duplicate assets in pctasks? -We should probably ingest items with
# an "insert" rather than "upsert" action so it fails if duplicate source
# data assets exist.

logger = logging.getLogger(__name__)
handler = logging.StreamHandler(stream=sys.stderr)
logger.addHandler(handler)
logger.setLevel(logging.INFO)
handler.setLevel(logging.INFO)


class GoesGlmCollection(Collection):
    @classmethod
    def create_item(
        cls, asset_uri: str, storage_factory: StorageFactory
    ) -> Union[List[pystac.Item], WaitTaskResult]:
        t0 = time.time()
        nc_storage, nc_asset_path = storage_factory.get_storage_for_file(asset_uri)

        # download the netcdf
        with TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            tmp_nc_asset_path = Path(tmp_dir, Path(nc_asset_path).name)
            nc_storage.download_file(nc_asset_path, tmp_nc_asset_path)

            # create item and geoparquet files (saved to same directory as the nc file)
            item = stac.create_item(tmp_nc_asset_path, nogeoparquet=True)

        # preference: slim down the source netcdf asset
        netcdf_asset_dict = item.assets["netcdf"].to_dict()
        netcdf_asset_dict.pop("cube:dimensions")
        netcdf_asset_dict.pop("cube:variables")
        item.assets["netcdf"] = pystac.Asset.from_dict(netcdf_asset_dict)
        item.stac_extensions.remove(DATACUBE_EXTENSION)
        item.assets["netcdf"].roles = ["data"]

        # preference: netCDF 4 to NetCDF4
        item.assets["netcdf"].title = "Original NetCDF4 file"

        # Update with remote URL
        item.assets["netcdf"].href = nc_storage.get_url(nc_asset_path)

        logger.info(
            "Processing asset_href=%s seconds=%s",
            asset_uri,
            round(time.time() - t0, 2),
        )

        return [item]
