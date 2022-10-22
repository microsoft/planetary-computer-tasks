from pathlib import Path
from tempfile import TemporaryDirectory
from typing import List, Union

import pystac
from stactools.noaa_mrms_qpe.stac import create_item, parse_filename
from stactools.noaa_mrms_qpe.constants import AOI

from pctasks.core.models.task import WaitTaskResult
from pctasks.core.storage import StorageFactory
from pctasks.dataset.collection import Collection

# COG_CONTAINER = "blob://mrms/mrms-cogs"
COG_CONTAINER = "blob://devstoreaccount1/mrms-cogs"


class NoaaMrmsQpeCollection(Collection):
    @classmethod
    def create_item(
        cls, asset_uri: str, storage_factory: StorageFactory
    ) -> Union[List[pystac.Item], WaitTaskResult]:

        meta = parse_filename(asset_uri)
        aoi = next(aoi for aoi in AOI if aoi in asset_uri)
        parts = asset_uri.split("/")
        path_fragment = "/".join(parts[4:7])

        with TemporaryDirectory() as tmp_dir:
            # download grib file
            grib_storage, grib_path = storage_factory.get_storage_for_file(asset_uri)
            tmp_grib_path = Path(tmp_dir, Path(grib_path).name)
            grib_storage.download_file(grib_path, tmp_grib_path)

            # create item
            item = create_item(tmp_grib_path, aoi)

            # update roles to be consistent in the PC
            item.assets["cog"].roles = ["data"]
            item.assets["grib2"].roles = ["data"]

            # temporary grammar fix
            item.assets["cog"].title = "Processed Cloud Optimized GeoTIFF file"

            # custom extension schema points to the main branch, which could change
            schema = (
                "https://raw.githubusercontent.com/stactools-packages/"
                "noaa-mrms-qpe/main/extension/schema.json"
            )
            item.stac_extensions.remove(schema)

            # upload cog to Azure
            cog_storage = storage_factory.get_storage(f"{COG_CONTAINER}/{path_fragment}/")
            cog_filename = meta.id + ".tif"
            cog_storage.upload_file(Path(tmp_dir, cog_filename), cog_filename)

            # update hrefs to point to Azure
            item.assets["cog"].href = cog_storage.get_url(cog_filename)
            item.assets["grib2"].href = grib_storage.get_url(grib_path)

        return [item]
