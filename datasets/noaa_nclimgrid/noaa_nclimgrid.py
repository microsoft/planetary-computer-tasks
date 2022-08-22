from tempfile import TemporaryDirectory
from typing import List, Union
from pathlib import Path

import pystac
from stactools.noaa_nclimgrid.stac import create_items
from stactools.noaa_nclimgrid.utils import nc_href_dict

from pctasks.core.storage import StorageFactory
from pctasks.core.models.task import WaitTaskResult
from pctasks.dataset.collection import Collection

COG_CONTAINER = "blob://devstoreaccount1/nclimgrid-cogs/"
# COG_CONTAINER = "blob://nclimgridwesteurope/nclimgrid-cogs/"

class MissingCogs(Exception):
    pass

class NoaaNclimgridCollection(Collection):
    @classmethod
    def create_item(
        cls, asset_uri: str, storage_factory: StorageFactory
    ) -> Union[List[pystac.Item], WaitTaskResult]:
        with TemporaryDirectory() as tmp_dir:
            tmp_nc_dir = Path(tmp_dir, "nc")
            tmp_cog_dir = Path(tmp_dir, "cog")
            Path.mkdir(tmp_nc_dir)
            Path.mkdir(tmp_cog_dir)

            # download the netcdfs
            all_nc_uris = nc_href_dict(asset_uri)
            for nc_uri in all_nc_uris.values():
                storage, nc_path = storage_factory.get_storage_for_file(nc_uri)
                tmp_nc_path = Path(tmp_nc_dir, Path(nc_path).name)
                storage.download_file(nc_path, tmp_nc_path)

            # create items and cogs
            items = create_items(tmp_nc_path, tmp_cog_dir)  # update to include netcdf assets?

            local_cogs = {f.name: f.as_posix() for f in tmp_cog_dir.glob("*.tif")}
            if len(local_cogs) != len(items) * 4:
                raise MissingCogs("not all cogs created")
            
            # upload cogs and update asset hrefs with new location
            cog_storage = storage_factory.get_storage(COG_CONTAINER)
            for item in items:
                for var in ["prcp", "tavg", "tmax", "tmin"]:
                    cog_filename = f"{var}-{item.id}.tif"
                    cog_storage.upload_file(local_cogs[cog_filename], cog_filename)                    
                    item.assets[var].href = cog_storage.get_url(cog_filename)
        
        return items