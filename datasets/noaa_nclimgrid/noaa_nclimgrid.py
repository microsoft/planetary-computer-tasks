from tempfile import TemporaryDirectory
from typing import List, Union
from pctasks.core.models.task import WaitTaskResult
from pctasks.core.storage import StorageFactory
import pystac
from pathlib import Path

from stactools.noaa_nclimgrid.stac import create_items
from stactools.noaa_nclimgrid.utils import nc_href_dict

from pctasks.dataset.collection import Collection

class NoaaNclimgridCollection(Collection):
    @classmethod
    def create_item(
        cls, asset_uri: str, storage_factory: StorageFactory  # where is create_item called from? Can we add another storage (for cogs)?
    ) -> Union[List[pystac.Item], WaitTaskResult]:

        with TemporaryDirectory() as tmp_dir:
            tmp_nc_dir = Path(tmp_dir, "nc").mkdir()
            tmp_cog_dir = Path(tmp_dir, "cog").mkdir()

            # download the netcdfs to a temporary directory
            all_nc_hrefs = nc_href_dict(asset_uri)
            for nc_href in all_nc_hrefs.values():
                storage, nc_path = storage_factory.get_storage_for_file(nc_href)
                tmp_nc_path = Path(tmp_nc_dir, nc_path)
                storage.download_file(nc_path, tmp_nc_path)

            # create items and cogs
            items = create_items(tmp_nc_path, tmp_cog_dir)  # update to include netcdf assets?
        
            # upload cogs to blob storage - need cog_storage

            # update cog hrefs from temporary to blob storage
        
        return items