import logging
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import List, Union

import pystac
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


class ESAWorldCoverCollection(Collection):
    @classmethod
    def create_item(
        cls, asset_uri: str, storage_factory: StorageFactory
    ) -> Union[List[pystac.Item], WaitTaskResult]:
        with TemporaryDirectory() as tmp_dir:
            storage, map_path = storage_factory.get_storage_for_file(asset_uri)
            map_name = Path(map_path).name
            tmp_map_path = str(Path(tmp_dir, map_name))

            quality_name = map_name.replace("_Map.tif", "_InputQuality.tif")
            quality_path = str(
                Path(map_path).parent.parent / "input_quality" / quality_name
            )
            tmp_quality_path = str(Path(tmp_dir, quality_name))

            storage.download_file(map_path, tmp_map_path)
            storage.download_file(quality_path, tmp_quality_path)

            item = create_item(
                map_href=tmp_map_path, include_quality_asset=True, raster_footprint=True
            )

            for key in item.assets:
                if key == "map":
                    asset_path = map_path
                elif key == "input_quality":
                    asset_path = quality_path
                else:
                    raise ValueError(f"Unexpected Item asset key '{key}'")
                item.assets[key].href = storage.get_url(asset_path)

        return [item]
