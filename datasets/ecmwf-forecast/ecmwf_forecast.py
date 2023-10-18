from typing import List, Union

import pystac
from stactools.ecmwf_forecast import stac

from pctasks.core.models.task import WaitTaskResult
from pctasks.core.storage import StorageFactory
from pctasks.dataset.collection import Collection


class EcmwfCollection(Collection):
    @classmethod
    def create_item(
        cls, asset_uri: str, storage_factory: StorageFactory
    ) -> Union[List[pystac.Item], WaitTaskResult]:
        asset_storage, asset_path = storage_factory.get_storage_for_file(asset_uri)

        grib2_href = asset_storage.get_url(asset_path)
        index_href = grib2_href.rsplit(".", 1)[0] + ".index"

        bad_files = ['blob://ai4edataeuwest/ecmwf/20220129/12z/0p4-beta/wave/20220129120000-162h-wave-fc.grib2']
        if grib2_href in bad_files:
            return []
        else:
            item = stac.create_item([grib2_href, index_href], split_by_step=True)
            return [item]