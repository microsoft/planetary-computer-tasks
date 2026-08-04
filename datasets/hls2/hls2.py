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


# regex for the STAC metadata blob path
hls2_regex = re.compile(r"([SL]30)/(\d{2})/([A-Z])/([A-Z]{2})/(\d{4})/(\d{2})/(\d{2})/HLS.[SL]30.T(\d{2})([A-Z]{3}).(\d{7})T(\d{6}).v2.0/.*_stac\.json")

STAC_JSON_SUFFIX = "_stac.json"

# Band assets (does not include thumbnail)
S30_assets = ['B01', 'B02', 'B03', 'B04', 'B05', 'B06', 'B07', 'B08', 'B8A', 'B09', 'B10', 'B11', 'B12', 'Fmask', 'SZA', 'SAA', 'VZA', 'VAA']
L30_assets = ['B01', 'B02', 'B03', 'B04', 'B05', 'B06', 'B07', 'B09', 'B10', 'B11', 'Fmask', 'SZA', 'SAA', 'VZA', 'VAA']

class HLS2Collection(Collection):
    @classmethod
    def create_item(
        cls, asset_uri: str, storage_factory: StorageFactory, upload: bool = True,
    ) -> Union[List[pystac.Item], WaitTaskResult]:
        # The asset_uri is the full blob uri path to the _stac.json file.
        # It used to be the .jpg browse image, but LP DAAC stopped publishing
        # that for HLSS30 around 2026-06-17.
        storage, stac_json_path = storage_factory.get_storage_for_file(asset_uri)

        if not storage.file_exists(stac_json_path):
            raise Exception(f"{stac_json_path} does not exist in {storage}")

        m = re.match(hls2_regex, stac_json_path)
        if not m:
            raise Exception(f"{stac_json_path} did not match regex")

        # ".../HLS.S30.T06WXC.2026213T212519.v2.0" - every sibling asset is
        # this prefix plus a suffix (".B01.tif", ".jpg", ...).
        base_path = stac_json_path[: -len(STAC_JSON_SUFFIX)]

        logger.debug("Reading existing STAC Item JSON from NASA")

        # Download STAC Item JSON provided by NASA
        with TemporaryDirectory() as tmp_dir:
            nc_name = os.path.basename(stac_json_path)
            tmp_nc_path = os.path.join(tmp_dir, nc_name)
            storage.download_file(stac_json_path, tmp_nc_path)
            try:
                item = pystac.Item.from_file(tmp_nc_path)
            except Exception as e:
                logger.error(f"Failed to read in STAC Item from {tmp_nc_path}: {e}")
                return []

        # Verify all band assets exist in blob
        if 'sentinel' in item.properties["platform"]:
            expected_assets = S30_assets
        elif 'landsat' in item.properties["platform"]:
            expected_assets = L30_assets
        else:
            logger.error(f"Unknown platform {item.properties['platform']}")
            return []

        for expected_asset in expected_assets:
            if not storage.file_exists(f"{base_path}.{expected_asset}.tif"):
                logger.error(f"{expected_asset} does not exist in {storage}")
                return []

        # Clear out links TODO: DO WE NEED ANY LINKS ADDED HERE?
        item.links = []

        # The browse image is optional - HLSS30 no longer ships one.
        has_thumbnail = storage.file_exists(f"{base_path}.jpg")

        # Update the hrefs and remove the stac JSON from the asset list
        base_uri_https = f"{storage.account_url}/{storage.container_name}/{base_path}"
        for asset in list(item.assets):
            if '.tif' in item.assets[asset].href:
                item.assets[asset].href = f"{base_uri_https}.{asset}.tif"
                # TODO - make sure this exists in blob
            elif asset == 'thumbnail':
                if has_thumbnail:
                    item.assets[asset].href = f"{base_uri_https}.jpg"
                else:
                    item.assets.pop(asset)
            elif STAC_JSON_SUFFIX in item.assets[asset].href:
                item.assets.pop(asset)

        # Some of the json we already copied had its extensions cleared, so add them back in
        if len(item.stac_extensions) == 0:
            item.stac_extensions = [
                "https://stac-extensions.github.io/eo/v1.0.0/schema.json",
                "https://stac-extensions.github.io/projection/v1.0.0/schema.json",
                "https://stac-extensions.github.io/view/v1.0.0/schema.json",
                "https://stac-extensions.github.io/scientific/v1.0.0/schema.json"
            ]

        return [item]
