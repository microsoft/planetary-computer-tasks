import logging
import os
from tempfile import TemporaryDirectory
from typing import List, Union

import pystac
import requests
import urllib3
from stactools.core.utils.antimeridian import Strategy, fix_item
from pctasks.core.storage.base import Storage
from stactools.sentinel1.grd import Format
from stactools.sentinel1.grd.stac import create_item

from pctasks.core.models.task import WaitTaskResult
from pctasks.core.storage import StorageFactory
from pctasks.core.utils.backoff import is_common_throttle_exception, with_backoff
from pctasks.dataset.collection import Collection

handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("[%(levelname)s]:%(asctime)s: %(message)s"))
handler.setLevel(logging.INFO)
logger = logging.getLogger(__name__)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

ASSET_INFO = {
    "vv": {
        "title": "VV: vertical transmit, vertical receive",
        "description": (
            "Amplitude of signal transmitted with "
            "vertical polarization and received with vertical polarization "
            "with radiometric terrain correction applied."
        ),
    },
    "vh": {
        "title": "VH: vertical transmit, horizontal receive",
        "description": (
            "Amplitude of signal transmitted with "
            "vertical polarization and received with horizontal polarization "
            "with radiometric terrain correction applied."
        ),
    },
    "hh": {
        "title": "HH: horizontal transmit, horizontal receive",
        "description": (
            "Amplitude of signal transmitted with "
            "horizontal polarization and received with horizontal polarization "
            "with radiometric terrain correction applied."
        ),
    },
    "hv": {
        "title": "HV: horizontal transmit, vertical receive",
        "description": (
            "Amplitude of signal transmitted with "
            "horizontal polarization and received with vertical polarization "
            "with radiometric terrain correction applied."
        ),
    },
    "thumbnail": {
        "title": "Preview Image",
        "description": (
            "An averaged, decimated preview image in PNG format. Single "
            "polarisation products are represented with a grey scale image. "
            "Dual polarisation products are represented by a single composite "
            "colour image in RGB with the red channel (R) representing the  "
            "co-polarisation VV or HH), the green channel (G) represents the "
            "cross-polarisation (VH or HV) and the blue channel (B) represents "
            "the ratio of the cross an co-polarisations."
        ),
    },
}


def backoff_throttle_check(e: Exception) -> bool:
    return (
        is_common_throttle_exception(e)
        or isinstance(e, urllib3.exceptions.ReadTimeoutError)
        or isinstance(e, requests.exceptions.ConnectionError)
    )


def get_item_storage(asset_uri: str, storage_factory: StorageFactory) -> Storage:
    is_blob_storage = asset_uri.startswith("blob://")
    # We also write the individual STAC items to a storage container
    # for another processing stream.
    stac_item_container_name = os.environ.get(
        "PCTASKS__S1GRD__STAC_ITEM_CONTAINER", "s1-grd-stac"
    )
    account_name = asset_uri.lstrip("blob://").split("/")[0]
    if is_blob_storage:
        prefix = f"blob://{account_name}/{stac_item_container_name}"
        # remove the blob prefix and the manifest.safe suffix
        path = os.path.dirname(asset_uri.split("/", 4)[-1])
    else:
        prefix = stac_item_container_name
        path = os.path.dirname(asset_uri)
    stac_item_storage = storage_factory.get_storage(f"{prefix}/{path}.json")
    return stac_item_storage


class S1GRDCollection(Collection):
    @classmethod
    def create_item(
        cls, asset_uri: str, storage_factory: StorageFactory
    ) -> Union[List[pystac.Item], WaitTaskResult]:
        """
        Create an item from an asset URI.

        Notes
        -----
        The asset URIs are like

           blob://<account>/<container>/GRD/2023/6/20/EW/DH/S1A_EW_GRDM_1SDH_20230620T020009_20230620T020113_049063_05E665_5673/manifest.safe  # noqa: E501
        """
        archive = os.path.dirname(asset_uri)
        archive_storage = storage_factory.get_storage(archive)
        stac_item_storage = get_item_storage(asset_uri, storage_factory)

        with TemporaryDirectory() as temp_dir:
            temp_archive_dir = os.path.join(temp_dir, os.path.basename(archive))
            os.mkdir(temp_archive_dir)
            for path in archive_storage.list_files():
                _, ext = os.path.splitext(path)
                if ext in [".tiff", ".tif"]:  # large COGs not needed
                    continue
                if "/" in path:
                    head, _ = os.path.split(path)
                    if not os.path.isdir(os.path.join(temp_archive_dir, head)):
                        os.makedirs(os.path.join(temp_archive_dir, head))
                with_backoff(
                    lambda: archive_storage.download_file(
                        path, os.path.join(temp_archive_dir, path)
                    ),
                    is_throttle=backoff_throttle_check,
                )

            try:
                item: pystac.Item = create_item(
                    temp_archive_dir, archive_format=Format.COG
                )
            except FileNotFoundError:
                logger.exception(
                    f"Missing file when attempting to create item for {asset_uri}"
                )
                return []

            for asset in item.assets.values():
                path = os.path.basename(asset.href)
                asset.href = archive_storage.get_url(path)

        # Remove checksum from id
        item.id = "_".join(item.id.split("_")[0:-1])

        # Remove providers
        item.properties.pop("providers", None)

        # Match existing Planetary Computer STAC Items
        item.common_metadata.constellation = "Sentinel-1"
        item.clear_links()
        item.add_link(
            pystac.Link(
                rel="license",
                target=(
                    "https://sentinel.esa.int/documents/247904/690755/"
                    "Sentinel_Data_Legal_Notice"
                ),
            )
        )

        # Remove eo:bands from assets; fix-up titles and descriptions
        for asset_key, asset in item.assets.items():
            if asset_key in ASSET_INFO:
                _ = asset.extra_fields.pop("eo:bands", None)
                asset.title = ASSET_INFO[asset_key]["title"]
                asset.description = ASSET_INFO[asset_key]["description"]

        # Remove EO extension
        item.stac_extensions = [
            ext for ext in item.stac_extensions if "/eo/" not in ext
        ]

        # Fix antimeridian crossing
        item = fix_item(item, Strategy.SPLIT)

        # Write out JSON item for downstream processing
        stac_item_storage.write_json(item.to_dict())

        return [item]
