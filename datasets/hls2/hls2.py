import logging
import os
import re
from typing import List, Union

import pystac
from tempfile import TemporaryDirectory

from pctasks.core.models.task import WaitTaskResult
from pctasks.core.storage import StorageFactory
from pctasks.dataset.collection import Collection

handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("[%(levelname)s]:%(asctime)s: %(message)s"))
handler.setLevel(logging.INFO)
logger = logging.getLogger(__name__)
logger.addHandler(handler)
logger.setLevel(logging.INFO)


# regex for the jpg blob path
hls2_regex = re.compile(r"([SL]30)/(\d{2})/([A-Z])/([A-Z]{2})/(\d{4})/(\d{2})/(\d{2})/HLS.[SL]30.T(\d{2})([A-Z]{3}).(\d{7})T(\d{6}).v2.0/.*\.jpg")

class HLS2Collection(Collection):
    @classmethod
    def create_item(
        cls, asset_uri: str, storage_factory: StorageFactory, upload: bool = True,
    ) -> Union[List[pystac.Item], WaitTaskResult]:
        # The asset_uri is the full blob uri path to the .jpg file
        storage, thumbnail_path = storage_factory.get_storage_for_file(asset_uri)

        if not storage.file_exists(thumbnail_path):
            raise Exception(f"{thumbnail_path} does not exist in {storage}")

        m = re.match(hls2_regex, thumbnail_path)
        if not m:
            raise Exception(f"{thumbnail_path} did not match regex")

        logger.debug("Reading existing STAC Item JSON from NASA")
        
        # Download STAC Item JSON provided by NASA
        stac_json_path = thumbnail_path.replace('.jpg', '_stac.json')
        with TemporaryDirectory() as tmp_dir:
            nc_name = os.path.basename(stac_json_path)
            tmp_nc_path = os.path.join(tmp_dir, nc_name)
            storage.download_file(stac_json_path, tmp_nc_path)
            try:
                item = pystac.Item.from_file(tmp_nc_path)
            except Exception as e:
                logger.error(f"Failed to read in STAC Item from {tmp_nc_path}: {e}")
                return []

        # Clear out links for now
        item.links = []

        # Update the hrefs and remove the stac JSON from the asset list
        thumbnail_uri_https = f"{storage.account_url}/{storage.container_name}/{thumbnail_path}"
        for asset in item.assets:
            if '.tif' in item.assets[asset].href:
                item.assets[asset].href = thumbnail_uri_https.replace('.jpg', f'.{asset}.tif')
                # TODO - make sure this exists in blob
            elif asset == 'thumbnail':
                item.assets[asset].href = thumbnail_uri_https # we've already checked this exists
            elif '_stac.json' in item.assets[asset].href:
                item.assets.pop(asset)
                # TODO - we should also make sure the json file isnt in blob

        # TODO - add in extensions
        '''
          "stac_extensions": [
            "https://stac-extensions.github.io/eo/v1.0.0/schema.json",
            "https://stac-extensions.github.io/projection/v1.0.0/schema.json",
            "https://stac-extensions.github.io/view/v1.0.0/schema.json",
            "https://stac-extensions.github.io/scientific/v1.0.0/schema.json"
        ]
        '''
        return [item]
