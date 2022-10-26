from pathlib import Path
from tempfile import TemporaryDirectory
from typing import List, Union

import pystac
from stactools.noaa_nclimgrid.stac import create_items
from stactools.noaa_nclimgrid.utils import nc_href_dict
from stactools.noaa_nclimgrid.constants import CollectionType

from pctasks.core.models.task import WaitTaskResult
from pctasks.core.storage import StorageFactory
from pctasks.dataset.collection import Collection

COG_CONTAINER = "blob://nclimgridwesteurope/nclimgrid-cogs"


class MissingCogs(Exception):
    pass


class NoaaNclimgridCollection(Collection):
    @classmethod
    def create_item(
        cls, asset_uri: str, storage_factory: StorageFactory
    ) -> Union[List[pystac.Item], WaitTaskResult]:
        collection_type = CollectionType.from_href(asset_uri).value

        with TemporaryDirectory() as tmp_dir:
            tmp_nc_dir = Path(tmp_dir, "nc")
            tmp_cog_dir = Path(tmp_dir, "cog")
            Path.mkdir(tmp_nc_dir)
            Path.mkdir(tmp_cog_dir)

            # download the netcdfs
            all_nc_urls = {}
            all_nc_uris = nc_href_dict(asset_uri)
            for var, nc_uri in all_nc_uris.items():
                nc_storage, nc_path = storage_factory.get_storage_for_file(nc_uri)
                tmp_nc_path = Path(tmp_nc_dir, Path(nc_path).name)
                nc_storage.download_file(nc_path, tmp_nc_path)
                all_nc_urls[var] = nc_storage.get_url(nc_path)

            # create items and cogs
            # explicitly do *not* include the source NetCDF assets.
            # We'll include those in a separate collection later and link to them.
            items, _ = create_items(tmp_nc_path, tmp_cog_dir, nc_assets=False)

            local_cogs = {f.name: f.as_posix() for f in tmp_cog_dir.glob("*.tif")}
            if len(local_cogs) != len(items) * 4:
                raise MissingCogs("not all cogs created")

            # upload cogs to Azure container; update cog and netcdf asset hrefs
            cog_storage = storage_factory.get_storage(
                f"{COG_CONTAINER}/nclimgrid-{collection_type}/"
            )
            for item in items:
                for var in ["prcp", "tavg", "tmax", "tmin"]:
                    if "daily" in collection_type:
                        cog_filename = f"{var}-{item.id}.tif"
                    else:
                        cog_filename = f"{item.id[0:9]}-{var}-{item.id[10:]}.tif"

                    cog_storage.upload_file(local_cogs[cog_filename], cog_filename)

                    item.assets[var].href = cog_storage.get_url(cog_filename)

        return items
