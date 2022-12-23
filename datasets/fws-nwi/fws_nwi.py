from pathlib import Path
from tempfile import TemporaryDirectory
from typing import List

from pystac import Item
from stactools.fws_nwi import stac
from stactools.fws_nwi.constants import ZIPFILE_ASSET_KEY

from pctasks.core.storage import StorageFactory
from pctasks.dataset.collection import Collection

GEOPARQUET_CONTAINER = "blob://ai4edataeuwest/fws-nwi/geoparquet"


class FwsNwiCollection(Collection):
    @classmethod
    def create_item(cls, asset_uri: str, storage_factory: StorageFactory) -> List[Item]:
        with TemporaryDirectory() as temporary_directory:
            storage, path = storage_factory.get_storage_for_file(asset_uri)
            local_path = Path(temporary_directory, Path(path).name)
            storage.download_file(path, str(local_path))
            item = stac.create_item(Path(local_path), Path(temporary_directory))

            geoparquet_storage = storage_factory.get_storage(
                f"{GEOPARQUET_CONTAINER}/{item.id}"
            )

            for key, asset in item.assets.items():
                if key == ZIPFILE_ASSET_KEY:
                    item.assets[key].href = storage.get_url(path)
                else:
                    geoparquet_path = Path(asset.href)
                    geoparquet_storage.upload_file(asset.href, geoparquet_path.name)
                    item.assets[key].href = geoparquet_storage.get_url(
                        geoparquet_path.name
                    )
        return [item]
