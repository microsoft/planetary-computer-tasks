import logging
import os
from typing import List, Union

import pystac
from azure.core.exceptions import ResourceNotFoundError
from stactools.core.utils.antimeridian import Strategy
from stactools.landsat import stac
from stactools.landsat.constants import Sensor

from pctasks.core.models.task import WaitTaskResult
from pctasks.core.storage import StorageFactory
from pctasks.dataset.collection import Collection

handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("[%(levelname)s]:%(asctime)s: %(message)s"))
handler.setLevel(logging.INFO)
logger = logging.getLogger(__name__)
logger.addHandler(handler)
logger.setLevel(logging.INFO)


class LandsatC2Collection(Collection):
    @classmethod
    def create_item(
        cls, asset_uri: str, storage_factory: StorageFactory
    ) -> Union[List[pystac.Item], WaitTaskResult]:

        storage, mtl_path = storage_factory.get_storage_for_file(asset_uri)
        if storage.get_file_info(mtl_path).size <= 0:
            logger.info("MTL file is empty")
            return []
        sensor = Sensor(os.path.basename(mtl_path)[1])

        # only look for ANG file if not MSS sensor
        if sensor is not Sensor.MSS:
            ang_path = mtl_path.replace("_MTL.xml", "_ANG.txt")
            try:
                if storage.get_file_info(ang_path).size <= 0:
                    logger.info("ANG file is empty")
                    return []
            except ResourceNotFoundError as e:
                logger.exception(e)
                logger.info("ANG file not found", exc_info=True)
                return []

        logger.info(f"Creating Item from MTL href: {mtl_path}")

        try:
            item = stac.create_stac_item(
                mtl_xml_href=storage.get_authenticated_url(mtl_path),
                legacy_l8=False,
                use_usgs_geometry=True,
                antimeridian_strategy=Strategy.NORMALIZE,
            )
            # We provide our own preview thumbnail
            item.assets.pop("thumbnail", None)
            item.assets.pop("reduced_resolution_browse", None)
        except Exception as e:
            logger.exception(e)
            logger.info("Error creating Item", exc_info=True)
            return []

        return [item]
