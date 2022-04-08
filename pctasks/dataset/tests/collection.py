from pathlib import Path
from typing import List, Union

import pystac
from pystac.utils import str_to_datetime

from pctasks.core.models.task import WaitTaskResult
from pctasks.core.storage import StorageFactory
from pctasks.dataset.collection import Collection


class TestCollection(Collection):
    def create_item(
        self, asset_uri: str, storage_factory: StorageFactory
    ) -> Union[List[pystac.Item], WaitTaskResult]:
        storage, path = storage_factory.get_storage_for_file(asset_uri)
        asset_json = storage.read_json(path)
        item = pystac.Item(
            id=Path(path).stem,
            geometry={
                "type": "Polygon",
                "coordinates": [[[0, 0], [0, 1], [1, 1], [1, 0], [0, 0]]],
            },
            bbox=[0, 0, 1, 1],
            datetime=str_to_datetime("2020-01-01T00:00:00Z"),
            properties={"name": asset_json["name"]},
        )
        item.add_asset(
            "data",
            pystac.Asset(
                href=asset_uri, media_type="application/json", title=Path(path).stem
            ),
        )
        return [item]
