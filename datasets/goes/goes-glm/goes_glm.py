import itertools
import logging
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
handler = logging.StreamHandler()
logger.setLevel(logging.INFO)
handler.setLevel(logging.INFO)
logger.addHandler(handler)


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
            try:
                item = stac.create_item(tmp_nc_asset_path, nogeoparquet=True)
            except OSError:
                # Some invalid NetCDF assets. For example
                # https://goeseuwest.blob.core.windows.net/noaa-goes17/GLM-L2-LCFA/2021/088/21/OR_GLM-L2-LCFA_G17_s20210882130200_e20210882130404_c20210882130418.nc   # noqa: E501
                # last modified at 2021-09-02T13:15:26.000Z
                logger.exception("Possibly invalid NetCDF file at %s", asset_uri)
                # TODO: need some mechanism for signaling ignore this?
                raise

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

        return [item]

    @classmethod
    def deduplicate_items(cls, items: List[pystac.Item]) -> List[pystac.Item]:
        logger.info("Deduplicating items")
        items = sorted(items, key=lambda x: x.id)
        items2 = []
        for _, v in itertools.groupby(items, key=lambda x: x.id):
            v2 = list(v)
            # the NetCDF file includes the processing datetime.
            # maximizing that will give the most recent item.
            item = max(v2, key=lambda x: x.assets["netcdf"].href)
            items2.append(item)

        logger.info("Deduplicated items. %s -> %s", len(items), len(items2))
        return items2

