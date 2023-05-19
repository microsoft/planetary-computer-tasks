import os
import logging
from typing import List, Union

import pystac
from stactools.landsat.constants import Sensor
from stactools.landsat import stac
from stactools.core.utils.antimeridian import Strategy
from azure.core.exceptions import ResourceNotFoundError

# from pctasks.core.pctasks.core.models.task import WaitTaskResult
# from pctasks.core.pctasks.core.storage import StorageFactory
# from pctasks.dataset.pctasks.dataset.collection import Collection

from pctasks.core.models.task import WaitTaskResult
from pctasks.core.storage import StorageFactory
from pctasks.dataset.collection import Collection

handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("[%(levelname)s]:%(asctime)s: %(message)s"))
handler.setLevel(logging.INFO)
logger = logging.getLogger(__name__)
logger.addHandler(handler)
logger.setLevel(logging.INFO)


class LandsatC2L1Collection(Collection):
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
                mtl_xml_href=mtl_path,
                legacy_l8=False,
                use_usgs_geometry=True,
                antimeridian_strategy=Strategy.NORMALIZE,
                read_href_modifier=storage.sign,
            )
            # We provide our own preview thumbnail
            item.assets.pop("thumbnail", None)
            item.assets.pop("reduced_resolution_browse", None)
        except Exception as e:
            logger.exception(e)
            logger.info("Error creating Item", exc_info=True)
            return []

        return [item]


if __name__ == "__main__":
    hrefs = [
        "/Users/pjh/data/landsat-c2/level-1/standard/mss/1972/005/037/LM01_L1GS_005037_19720823_20200909_02_T2/LM01_L1GS_005037_19720823_20200909_02_T2_MTL.xml",
        "/Users/pjh/data/landsat-c2/level-2/standard/tm/1986/010/067/LT05_L2SP_010067_19860424_20200918_02_T2/LT05_L2SP_010067_19860424_20200918_02_T2_MTL.xml",
        "/Users/pjh/data/landsat-c2/level-2/standard/oli-tirs/2022/160/076/LC08_L2SP_160076_20220305_20220314_02_T1/LC08_L2SP_160076_20220305_20220314_02_T1_MTL.xml",
        "/Users/pjh/data/landsat-c2/level-2/standard/etm/2010/021/030/LE07_L2SP_021030_20100109_20200911_02_T1/LE07_L2SP_021030_20100109_20200911_02_T1_MTL.xml"
    ]
    for href in hrefs:
        storage_factory = StorageFactory()
        c = LandsatC2L1Collection()
        item = c.create_item(href, storage_factory)[0]
        item.validate()
        import json
        with open(f"{item.id}.json", "w") as f:
            json.dump(item.to_dict(), f, indent=4)