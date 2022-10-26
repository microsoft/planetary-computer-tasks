import os
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


class GoesGlmCollection(Collection):
    @classmethod
    def create_item(
        cls, asset_uri: str, storage_factory: StorageFactory
    ) -> Union[List[pystac.Item], WaitTaskResult]:
        nc_storage, nc_asset_path = storage_factory.get_storage_for_file(asset_uri)

        # download the netcdf
        with TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            tmp_nc_asset_path = Path(tmp_dir, Path(nc_asset_path).name)
            nc_storage.download_file(nc_asset_path, tmp_nc_asset_path)

            # create item and geoparquet files (saved to same directory as the nc file)
            item = stac.create_item(tmp_nc_asset_path)
            tmp_parquets = {f.name: f.as_posix() for f in tmp_dir.glob("*.parquet")}

            # preference: slim down the source netcdf asset
            netcdf_asset_dict = item.assets["netcdf"].to_dict()
            netcdf_asset_dict.pop("cube:dimensions")
            netcdf_asset_dict.pop("cube:variables")
            item.assets["netcdf"] = pystac.Asset.from_dict(netcdf_asset_dict)
            item.stac_extensions.remove(DATACUBE_EXTENSION)

            # preference: remove "cloud-optimized" role to be consistent in the PC
            for key_suffix in ["events", "flashes", "groups"]:
                item.assets[f"geoparquet_{key_suffix}"].roles = ["data"]
            # preference: remove "source" role to be consistent in the PC
            item.assets["netcdf"].roles = ["data"]

            # preference: netCDF 4 to NetCDF4
            item.assets["netcdf"].title = "Original NetCDF4 file"

            # upload geoparquets; update geoparquet and netcdf asset hrefs
            parquet_storage = storage_factory.get_storage(f"{GEOPARQUET_CONTAINER}")
            satellite_number = item.properties["platform"][-2:]
            for tmp_name, tmp_path in tmp_parquets.items():
                upload_path = (
                    f"goes-{satellite_number}/{os.path.splitext(nc_asset_path)[0]}_{tmp_name}"
                )
                parquet_storage.upload_file(tmp_path, upload_path)

                key = f"geoparquet_{tmp_name[:-8]}"
                item.assets[key].href = parquet_storage.get_url(upload_path)

            item.assets["netcdf"].href = nc_storage.get_url(nc_asset_path)

        return [item]