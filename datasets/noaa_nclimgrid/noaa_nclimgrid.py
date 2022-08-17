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
        cls, asset_uri: str, storage_factory: StorageFactory
    ) -> Union[List[pystac.Item], WaitTaskResult]:

        with TemporaryDirectory() as tmp_dir:
            tmp_nc_dir = Path(tmp_dir, "nc")
            tmp_cog_dir = Path(tmp_dir, "cog")
            Path.mkdir(tmp_nc_dir)
            Path.mkdir(tmp_cog_dir)

            # download the netcdfs to a temporary directory
            all_nc_uris = nc_href_dict(asset_uri)
            for nc_uri in all_nc_uris.values():
                storage, nc_path = storage_factory.get_storage_for_file(nc_uri)
                tmp_nc_path = Path(tmp_nc_dir, Path(nc_path).name)
                storage.download_file(nc_path, tmp_nc_path)

            # create items and cogs
            items = create_items(tmp_nc_path, tmp_cog_dir)  # update to include netcdf assets?
        
            # # upload cogs to blob storage - need cog_storage
            # cog_uri = "blob://nclimgridcogstorageaccount/nclimgridcogstoragecontainer"
            # cog_storage = storage_factory.get_storage(cog_uri)
            # cog_storage.upload_file()

            # update cog hrefs from temporary to blob storage
        
        return items


# def lets_test_some_stuff():
#     with TemporaryDirectory() as tmp_dir:
#         tmp_nc_dir = Path(tmp_dir, "nc")
#         tmp_cog_dir = Path(tmp_dir, "cog")
#         Path.mkdir(tmp_nc_dir)
#         Path.mkdir(tmp_cog_dir)

#         asset_uri = "blob://nclimgridwesteurope/nclimgrid/nclimgrid-daily/beta/by-month/2022/01/prcp-202201-grd-scaled.nc"

#         # download the netcdfs to a temporary directory
#         all_nc_uris = nc_href_dict(asset_uri)
#         storage_factory = StorageFactory()
#         for nc_uri in all_nc_uris.values():
#             storage, nc_path = storage_factory.get_storage_for_file(nc_uri)
#             tmp_nc_path = Path(tmp_nc_dir, Path(nc_path).name)
#             print(nc_uri)
#             print(nc_path)
#             print(tmp_nc_path)
#             print(storage.__repr__)
#             storage.download_file(nc_path, tmp_nc_path)
#             exit()


# if __name__ == "__main__":
#     lets_test_some_stuff()
