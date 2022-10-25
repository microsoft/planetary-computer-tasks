import logging
from pathlib import PurePath
from tempfile import TemporaryDirectory
from typing import List, Union

import pystac
from stactools.noaa_climate_normals.tabular.stac import (
    create_item as tabular_create_item,
)

from pctasks.core.models.task import WaitTaskResult
from pctasks.core.storage import StorageFactory
from pctasks.dataset.collection import Collection


class NoaaClimateNormalsTabular(Collection):
    @classmethod
    def create_item(
        cls, asset_uri: str, storage_factory: StorageFactory
    ) -> Union[List[pystac.Item], WaitTaskResult]:

        logger = logging.getLogger(__name__)
        logger.info(f"Asset URI = {asset_uri}")
        print(asset_uri)

        return []
