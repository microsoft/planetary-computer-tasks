import logging
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Union

import pystac
import rasterio
from pystac.utils import datetime_to_str, str_to_datetime
from stactools.core.utils.raster_footprint import RasterFootprint

from pctasks.core.models.task import WaitTaskResult
from pctasks.core.storage import StorageFactory
from pctasks.dataset.collection import Collection

NDJSON_PATH = "blob://pcdata01euw/impact/bii-v1/io-vizz-bii.ndjson"
ASSET_KEY = "data"

handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("[%(levelname)s]:%(asctime)s: %(message)s"))
handler.setLevel(logging.INFO)
logger = logging.getLogger(__name__)
logger.addHandler(handler)
logger.setLevel(logging.INFO)


@lru_cache(maxsize=1)
def get_ndjson(storage_factory: StorageFactory) -> Dict[str, Dict[str, Any]]:
    storage, path = storage_factory.get_storage_for_file(NDJSON_PATH)
    item_dicts = storage.read_ndjson(path)
    return {item["id"]: item for item in item_dicts}


class IOBiodiversityIntactnessIndex(Collection):
    @classmethod
    def create_item(
        cls, asset_uri: str, storage_factory: StorageFactory
    ) -> Union[List[pystac.Item], WaitTaskResult]:
        asset_storage, asset_path = storage_factory.get_storage_for_file(asset_uri)

        asset_href = asset_storage.get_authenticated_url(asset_path)
        with rasterio.open(asset_href) as src:
            geometry = RasterFootprint(
                data_array=src.read_masks(1),
                crs=src.crs,
                transform=src.transform,
                densification_distance=src.transform[0],
                simplify_tolerance=0.0005,
                no_data=0,
            ).footprint()

        if geometry is None:
            return []

        id = Path(asset_path).stem
        logger.info(f"geometry for {id}:\n{geometry}")
        io_item_dicts = get_ndjson(storage_factory)
        item_dict = io_item_dicts[id]

        item_dict["geometry"] = geometry

        asset_dict = item_dict["assets"].pop("asset")
        asset_dict["title"] = "Biodiversity Intactness Index"
        asset_dict["description"] = (
            "Modelled average abundance of originally-present species, expressed "
            "as a percentage, relative to their abundance in an intact ecosystem."
        )
        asset_dict["href"] = asset_storage.get_url(asset_path)
        asset_dict["type"] = pystac.MediaType.COG
        asset_dict["roles"] = ["data"]
        asset_dict["version"] = "v1"
        asset_dict["raster:bands"][0].pop("scale", None)
        asset_dict["raster:bands"][0].pop("offset", None)
        asset_dict["raster:bands"][0].pop("statistics", None)
        asset_dict["raster:bands"][0].pop("histogram", None)
        asset_dict["raster:bands"][0]["spatial_resolution"] = 100
        item_dict["assets"][ASSET_KEY] = asset_dict

        start_datetime = str_to_datetime(item_dict["properties"]["datetime"])
        end_datetime = datetime(start_datetime.year, 12, 31, 23, 59, 59)
        item_dict["properties"]["datetime"] = None
        item_dict["properties"]["start_datetime"] = datetime_to_str(start_datetime)
        item_dict["properties"]["end_datetime"] = datetime_to_str(end_datetime)

        item_dict["properties"].pop("proj:geometry", None)
        item_dict["properties"].pop("proj:bbox", None)

        item_dict["links"] = []
        item_dict.pop("collection", None)

        item_dict["stac_extensions"].append(
            "https://stac-extensions.github.io/version/v1.1.0/schema.json"
        )

        return [pystac.Item.from_dict(item_dict)]
