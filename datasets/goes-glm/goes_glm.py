import os
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import List, Union

import pystac
from stactools.goes_glm import stac

from pctasks.core.models.task import WaitTaskResult
from pctasks.core.storage import StorageFactory
from pctasks.dataset.collection import Collection

# GEOPARQUET_CONTAINER = "blob://devstoreaccount1/noaa-goes-geoparquet/"
GEOPARQUET_CONTAINER = "blob://goeseuwest/noaa-goes-geoparquet/"

# The original GOES ETL code indicates duplicate assets. Is there a way to
# handle duplicate assets in pctasks? Default item ingest is an upsert, so
# the ingest should not fail even with duplicates, but no logic is applied to
# decide which duplicate asset/item to ingest.


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

            # strip processing time off of item id
            item.id = item.id[0:item.id.find("_c")]
            # slim down the source netcdf asset
            item.assets["netcdf"].pop("cube:dimensions")
            item.assets["netcdf"].pop("cube:variables")

            # upload geoparquets; update geoparquet and netcdf asset hrefs
            parquet_storage = storage_factory.get_storage(f"{GEOPARQUET_CONTAINER}")
            for tmp_name, tmp_path in tmp_parquets.items():
                satellite_number = Path(nc_asset_path).name[16:18]
                upload_path = (
                    f"goes-{satellite_number}/{os.path.splitext(nc_asset_path)[0]}_{tmp_name}"
                )
                parquet_storage.upload_file(tmp_path, upload_path)

                asset_key = f"geoparquet_{tmp_name[0:-8]}"
                item.assets[asset_key].href = parquet_storage.get_url(upload_path)

                item.assets["netcdf"].href = nc_storage.get_url(nc_asset_path)

        return [item]
