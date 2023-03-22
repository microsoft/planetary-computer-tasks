import logging
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import List, Optional, Union

import numpy as np
import numpy.typing as npt
import pystac
import rasterio
from shapely.geometry import shape
from shapely.geometry.multipolygon import MultiPolygon
from shapely.geometry.polygon import Polygon
from stactools.core.utils.raster_footprint import RasterFootprint
from stactools.esa_worldcover.stac import create_item

from pctasks.core.models.task import WaitTaskResult
from pctasks.core.storage import StorageFactory
from pctasks.dataset.collection import Collection

handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("[%(levelname)s]:%(asctime)s: %(message)s"))
handler.setLevel(logging.INFO)
logger = logging.getLogger(__name__)
logger.addHandler(handler)
logger.setLevel(logging.INFO)


# This subclass is a workaround for node out-of-memory failures when computing
# the data mask (the worldcover tiles are large: 36,000x36,000 pixels). We
# bypass the mask creation and use the mask offered by rasterio. Since rasterio
# masks use a valid data value of 255 rather than 1, we also override the
# `data_extent` method. We do not convert the rasterio mask valid data value of
# 255 to 1, as the conversion logic (np.where()) is the same as that which
# causes the out-of-memory failure.
#
# This subclass may eventually be pushed to the stactools package.
class RioMaskRasterFootprint(RasterFootprint):
    def data_mask(self) -> npt.NDArray[np.uint8]:
        # we are passing rasterio masks as the data array
        return self.data_array

    def data_extent(self, mask: npt.NDArray[np.uint8]) -> Optional[Polygon]:
        data_polygons = [
            shape(polygon_dict)
            for polygon_dict, region_value in rasterio.features.shapes(
                mask, transform=self.transform
            )
            if region_value == 255  # rasterio masks use 255 (not 1)
        ]
        if not data_polygons:
            return None
        elif len(data_polygons) == 1:
            polygon = data_polygons[0]
        else:
            polygon = MultiPolygon(data_polygons).convex_hull
        return polygon


class ESAWorldCoverCollection(Collection):
    @classmethod
    def create_item(
        cls, asset_uri: str, storage_factory: StorageFactory
    ) -> Union[List[pystac.Item], WaitTaskResult]:
        with TemporaryDirectory() as tmp_dir:
            logger.info(f"asset uri = {asset_uri}")
            storage, map_path = storage_factory.get_storage_for_file(asset_uri)
            logger.info(f"map path = {map_path}")
            map_name = Path(map_path).name
            tmp_map_path = str(Path(tmp_dir, map_name))

            quality_name = map_name.replace("_Map.tif", "_InputQuality.tif")
            quality_path = str(
                Path(map_path).parent.parent / "input_quality" / quality_name
            )
            logger.info(f"quality path = {quality_path}")
            tmp_quality_path = str(Path(tmp_dir, quality_name))

            storage.download_file(map_path, tmp_map_path)
            storage.download_file(quality_path, tmp_quality_path)

            item = create_item(map_href=tmp_map_path, include_quality_asset=True)

            with rasterio.open(tmp_map_path) as src:
                assert src.nodata == 0
                footprint = RioMaskRasterFootprint(
                    data_array=src.read_masks(1),
                    crs=src.crs,
                    transform=src.transform,
                    densification_distance=0.001,  # roughly 100 meters (10 pixels)
                    simplify_tolerance=0.0001,  # roughly 10 meters (1 pixel)
                    no_data=src.nodata,
                ).footprint()
            item.geometry = footprint
            item.bbox = list(shape(item.geometry).bounds)

            for key, value in item.assets.items():
                if key == "map":
                    asset_path = map_path
                elif key == "input_quality":
                    asset_path = quality_path
                else:
                    raise ValueError(f"Unexpected Item asset key '{key}'")
                item.assets[key].href = storage.get_url(asset_path)

        return [item]
