import os
import logging
from typing import List, Union, Optional
import re

import lxml.etree
import pystac
from stactools.sentinel2 import stac
from stactools.core.utils.antimeridian import Strategy
from stactools.sentinel2.safe_manifest import SafeManifest

from pctasks.core.models.task import WaitTaskResult
from pctasks.core.storage import StorageFactory
from pctasks.dataset.collection import Collection
from pctasks.core.utils.backoff import with_backoff

handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("[%(levelname)s]:%(asctime)s: %(message)s"))
handler.setLevel(logging.INFO)
logger = logging.getLogger(__name__)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

DOWNSAMPLED_BAND_KEY_RX = re.compile(r"B.*_[\d]+m")

# We removed downsampled versions of these assets, so only take the lowest
# resolution and rename the asset key so to the generalized name. Also set the
# gsd since we lose the resolution in the key name
DOWNSAMPLE_ASSETS = {
    "AOT": ("10m", 10.0),
    "SCL": ("20m", 20.0),
    "WVP": ("10m", 10.0),
    "visual": ("10m", 10.0),
}

def is_throttle_exc(e: Exception) -> bool:
    """Checks if there's an XML parse error, which has been seen in throttle
    situations."""
    return isinstance(e, lxml.etree.XMLSyntaxError)


class Sentinel2Collection(Collection):  # type: ignore
    @classmethod
    def create_item(
        cls, asset_uri: str, storage_factory: StorageFactory
    ) -> Union[List[pystac.Item], WaitTaskResult]:
        asset_storage, granule_path = storage_factory.get_storage_for_file(asset_uri)
        granule_href = asset_storage.get_url(granule_path)

        if not asset_storage.file_exists(os.path.join(granule_path, "manifest.safe")):
            logger.error(f"Missing manifest file for granule: {granule_path}")
            return []

        manifest = with_backoff(
            lambda: SafeManifest(granule_href, asset_storage.sign),
            is_throttle=is_throttle_exc,
        )

        for href_opt, name in {
            manifest.product_metadata_href: "PRODUCT_METADATA",
            manifest.granule_metadata_href: "GRANULE_METADATA",
        }.items():
            if href_opt is None:
                logger.error(f"Missing {name} file for granule: {granule_path}")
                return []
            file_path = os.path.relpath(href_opt, granule_href)
            if not asset_storage.file_exists(os.path.join(granule_path, file_path)):
                logger.error(f"Missing {name} file for granule: {granule_path}")
                return []

        def get_item() -> pystac.Item:
            # Antimeridian geometries are "normalized"
            item: pystac.Item = stac.create_item(
                granule_href=granule_href,
                read_href_modifier=asset_storage.sign,
                antimeridian_strategy=Strategy.NORMALIZE,
                coordinate_precision=7,
            )
            return item

        item = with_backoff(
            get_item,
            is_throttle=is_throttle_exc,
        )

        # Remove providers from properties
        item.properties.pop("providers", None)

        # Remove downsampled version of assets as we don't host them
        filtered_assets = {}
        include_key: Optional[str] = None
        for k, asset in item.assets.items():
            include_key = k
            if re.match(DOWNSAMPLED_BAND_KEY_RX, k):
                include_key = None
            else:
                for ds_k, (target_m, target_gsd) in DOWNSAMPLE_ASSETS.items():
                    if k.startswith(ds_k):
                        if k.endswith(target_m):
                            include_key = ds_k
                            pystac.CommonMetadata(asset).gsd = target_gsd
                        else:
                            include_key = None
            if include_key:
                filtered_assets[include_key] = asset
        item.assets = filtered_assets

        # Add titles to metadata assets
        titles_to_add = {
            "preview": "Thumbnail",
            "safe-manifest": "SAFE manifest",
            "product-metadata": "Product metadata",
            "granule-metadata": "Granule metadata",
            "inspire-metadata": "INSPIRE metadata",
            "datastrip-metadata": "Datastrip metadata",
        }

        for asset_key in item.assets:
            if asset_key in titles_to_add:
                item.assets[asset_key].title = titles_to_add[asset_key]

        return [item]
