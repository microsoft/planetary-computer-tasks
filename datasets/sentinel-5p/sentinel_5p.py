import logging
import os
from tempfile import TemporaryDirectory
from typing import List, Union

import pystac
from stactools.sentinel5p.stac import create_item

from pctasks.core.models.task import WaitTaskResult
from pctasks.core.storage import StorageFactory
from pctasks.dataset.collection import Collection

handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("[%(levelname)s]:%(asctime)s: %(message)s"))
handler.setLevel(logging.INFO)
logger = logging.getLogger(__name__)
logger.addHandler(handler)
logger.setLevel(logging.INFO)


class Sentinel5pNetCDFCollection(Collection):
    @classmethod
    def create_item(
        cls, asset_uri: str, storage_factory: StorageFactory
    ) -> Union[List[pystac.Item], WaitTaskResult]:
        storage, nc_path = storage_factory.get_storage_for_file(asset_uri)

        with TemporaryDirectory() as tmp_dir:
            nc_name = os.path.basename(nc_path)
            tmp_nc_path = os.path.join(tmp_dir, nc_name)
            storage.download_file(nc_path, tmp_nc_path)
            item = create_item(tmp_nc_path)

        # Set the asset href to the blob storage URL
        list(item.assets.values())[0].href = storage.get_url(nc_path)

        # providers is supplied in the Collection
        item.properties.pop("providers", None)

        # match existing Item asset (no description)
        for asset in item.assets.values():
            asset.description = None

        # match existing Item ID pattern
        parts = item.id.split("_")
        item.id = parts[0] + "_" + parts[2] + "_" + "_".join(parts[4:-3])

        # correct bad datetimes
        for k, v in item.properties.items():
            if k.endswith("datetime") and v.endswith("ZZ"):
                item.properties[k] = v[:-2] + "Z"

        prefix = item.properties["s5p:product_name"].replace("-", "_")
        if prefix.startswith("np"):
            prefix = prefix.replace("_", "")

        if f"s5p:{prefix}" in item.properties:
            for k, v in item.properties[f"s5p:{prefix}"].items():
                if k.endswith("datetime") and v.endswith("ZZ"):
                    item.properties[f"s5p:{prefix}"][k] = v[:-2] + "Z"

        return [item]
