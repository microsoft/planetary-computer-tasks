from pathlib import Path
from tempfile import TemporaryDirectory
from typing import List, Union

import pystac
from stactools.noaa_mrms_qpe.stac import create_item, parse_filename

from pctasks.core.models.task import WaitTaskResult
from pctasks.core.storage import StorageFactory
from pctasks.dataset.collection import Collection

COG_CONTAINER = "blob://mrms/mrms-cogs"
AOIS = ["ALASKA", "CARIB", "CONUS", "GUAM", "HAWAII"]


class MissingCogs(Exception):
    pass


class NoaaNclimgridCollection(Collection):
    @classmethod
    def create_item(
        cls, asset_uri: str, storage_factory: StorageFactory
    ) -> Union[List[pystac.Item], WaitTaskResult]:

        # parse collection
        meta = parse_filename(asset_uri)
        # parts = Path(asset_uri).name.split("_")
        # accumulation_length = int(parts[3][0:2])
        # pass_number = parts[4].lower()
        collection = f"noaa-mrms-qpe-{meta.period}h-pass{meta.pass_no}"

        # parse aoi
        aoi = next(aoi for aoi in AOIS if aoi in asset_uri)

        with TemporaryDirectory() as tmp_dir:
            # download grib file
            grib_storage, grib_path = storage_factory.get_storage_for_file(asset_uri)
            tmp_grib_path = Path(tmp_dir, Path(grib_path).name)
            grib_storage.download_file(grib_path, tmp_grib_path)

            item = create_item(tmp_grib_path, aoi)

            # upload cog to Azure
            cog_storage = storage_factory.get_storage(f"{COG_CONTAINER}/{collection}/")
            cog_filename = meta.id + ".tif"
            cog_storage.upload_file(Path(tmp_dir, cog_filename), cog_filename)

            # update hrefs to point to Azure
            item.assets["cog"].href = cog_storage.get_url(cog_filename)
            item.assets["grib2"].href = grib_storage.get_url(grib_path)

        return [item]
