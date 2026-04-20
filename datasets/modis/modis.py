import logging
import os
from tempfile import TemporaryDirectory
from typing import List, Union

import pystac
import stactools.modis.cog
import stactools.modis.stac
from stactools.modis.file import File

from pctasks.core.models.task import WaitTaskResult
from pctasks.core.storage import StorageFactory
from pctasks.dataset.collection import Collection

handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("[%(levelname)s]:%(asctime)s: %(message)s"))
handler.setLevel(logging.INFO)
logger = logging.getLogger(__name__)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

COG_CONTAINER = "blob://modiseuwest/modis-061-cogs/"


# Add back in the platform property which NASA removed from their XML on March 13 2024
# On the MODIS side terra is distributed as MOD and aqua as MYD,
# but Within MPC both are distributed as MODxxx
# Copied the method from misc.py and deleted the file
def add_platform_field(item, href, logger):
    """
    add_platform_field # noqa: E501

    Adds the platform field to a STAC item based on the HDF file href.
    NASA removed this property from their XML metadata on March 13, 2024.

    :param item: The STAC item to update
    :type item: pystac.Item
    :param href: The href path containing MOD/MYD/MCD prefix
    :type href: str
    :param logger: Logger instance for debug/warning messages
    :type logger: logging.Logger
    :return: The updated STAC item with platform field
    :rtype: pystac.Item
    """
    if ("platform" not in item.properties) or (item.properties["platform"] == ""):
        logger.debug("platform field missing, filling it in based on original xml href")
        try:
            if href.split('/')[4][0:3] == "MOD":
                item.properties["platform"] = "terra"
            elif href.split('/')[4][0:3] == "MYD":
                item.properties["platform"] = "aqua"
            elif href.split('/')[4][0:3] == "MCD":
                item.properties["platform"] = "terra,aqua"
            else:
                logger.warning("href did not contain MOD/MYD/MCD in the usual spot")
        except Exception as e:
            logger.warning(f"href did not contain MOD/MYD/MCD in the usual spot, got error: {e}")
    return item


class MODISCollection(Collection):
    @classmethod
    def create_item(
        cls, asset_uri: str, storage_factory: StorageFactory
    ) -> Union[List[pystac.Item], WaitTaskResult]:

        logger.debug(f"asset_uri: {asset_uri}")

        asset_storage, asset_path = storage_factory.get_storage_for_file(asset_uri)
        if not asset_storage.file_exists(asset_path):
            raise ValueError(f"{asset_uri} does not exist")

        prefix = os.path.dirname(asset_path)
        cog_storage = storage_factory.get_storage(os.path.join(COG_CONTAINER, prefix))
        cog_paths = list(cog_storage.list_files(extensions=[".tif"]))
        create_cogs = not cog_paths
        if cog_paths:
            logger.debug(f"{len(cog_paths)} discovered in {prefix}")
        else:
            logger.debug(f"No COGs found in {prefix}")

        with TemporaryDirectory() as temporary_directory:
            file = File(os.path.join(temporary_directory, os.path.basename(asset_uri)))
            logger.debug(f"Downloading {asset_uri}")
            asset_storage.download_file(asset_path, file.hdf_href)

            logger.debug("Creating item")
            item = stactools.modis.stac.create_item(file.hdf_href)

            if create_cogs:
                logger.debug(f"Adding COGS to item {item}")
                paths, subdataset_names = stactools.modis.cog.add_cogs(
                    item, temporary_directory, create=True
                )
                for (path, subdataset_name) in zip(paths, subdataset_names):
                    file_name = os.path.basename(path)
                    href = cog_storage.get_url(file_name)
                    logger.debug(f"Uploading COG to {href}")
                    cog_storage.upload_file(
                        path, file_name, content_type=pystac.MediaType.COG
                    )
                    item.assets[subdataset_name].href = href
            else:
                logger.debug("Adding COG assets pointing to already-existing COGs")
                hrefs = [cog_storage.get_url(path) for path in cog_paths]
                stactools.modis.cog.add_cog_assets(item, hrefs)

        file = File(asset_storage.get_url(asset_path))
        logger.debug(f"Setting HDF asset href to {file.hdf_href}")
        item.assets["hdf"].href = file.hdf_href

        # Remove metadata asset if it exists since XML files are no longer provided
        if "metadata" in item.assets:
            del item.assets["metadata"]

        item = add_platform_field(item, file.hdf_href, logger)

        return [item]
