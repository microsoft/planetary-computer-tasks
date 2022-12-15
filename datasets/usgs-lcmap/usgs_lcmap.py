from pathlib import Path
from tempfile import TemporaryDirectory
from typing import List, Union

import pystac
from stactools.usgs_lcmap.stac import create_item
from stactools.usgs_lcmap.utils import get_variable_asset_info

from pctasks.core.models.task import WaitTaskResult
from pctasks.core.storage import StorageFactory
from pctasks.dataset.collection import Collection


class USGSLCMAPCollection(Collection):
    @classmethod
    def create_item(
        cls, asset_uri: str, storage_factory: StorageFactory
    ) -> Union[List[pystac.Item], WaitTaskResult]:

        with TemporaryDirectory() as tmp_dir:
            storage, tar_path = storage_factory.get_storage_for_file(asset_uri)
            xml_path = str(Path(tar_path).with_suffix(".xml"))
            tmp_tar_path = str(Path(tmp_dir, Path(tar_path).name))
            tmp_xml_path = str(Path(tmp_dir, Path(xml_path).name))
            storage.download_file(tar_path, tmp_tar_path)
            storage.download_file(xml_path, tmp_xml_path)

            item = create_item(tmp_tar_path)

            tmp_asset_paths = Path(tmp_tar_path).with_suffix("").glob("*.*")
            asset_keys_tmp_paths = get_variable_asset_info(tmp_asset_paths)
            for key, value in asset_keys_tmp_paths.items():
                asset_path = str(Path(tar_path).with_suffix("") / Path(value["href"]).name)
                storage.upload_file(value["href"], asset_path)
                item.assets[key].href = storage.get_url(asset_path)
            item.assets["tar"].href = storage.get_url(tar_path)
            item.assets["tar_metadata"].href = storage.get_url(xml_path)

        return item
