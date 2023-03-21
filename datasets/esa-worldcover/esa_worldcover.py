from pathlib import Path
from tempfile import TemporaryDirectory
from typing import List, Union

import pystac
from stactools.esa_worldcover.stac import create_item

from pctasks.core.models.task import WaitTaskResult
from pctasks.core.storage import StorageFactory
from pctasks.dataset.collection import Collection


class ESAWorldCoverCollection(Collection):
    @classmethod
    def create_item(
        cls, asset_uri: str, storage_factory: StorageFactory
    ) -> Union[List[pystac.Item], WaitTaskResult]:
        with TemporaryDirectory() as tmp_dir:
            storage, map_path = storage_factory.get_storage_for_file(asset_uri)
            tmp_map_path = str(Path(tmp_dir, Path(map_path).name))
            inputquality_path = map_path.replace("_Map.tif", "_InputQuality.tif")
            tmp_inputquality_path = tmp_map_path.replace(
                "_Map.tif", "_InputQuality.tif"
            )

            storage.download_file(map_path, tmp_map_path)
            storage.download_file(inputquality_path, tmp_inputquality_path)

            item = create_item(map_href=tmp_map_path, include_quality_asset=True)

            for key, value in item.assets.items():
                asset_path = str(Path(map_path).parent / Path(value.href).name)
                item.assets[key].href = storage.get_url(asset_path)

        return [item]
