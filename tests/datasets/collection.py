from datetime import datetime
from pathlib import Path
from typing import List, Union

import pystac

from pctasks.core.models.task import WaitTaskResult
from pctasks.core.storage import StorageFactory
from pctasks.dataset.collection import Collection


class TestCollection(Collection):
    def create_item(
        self, asset_uri: str, storage_factory: StorageFactory
    ) -> Union[List[pystac.Item], WaitTaskResult]:
        storage, path = storage_factory.get_storage_for_file(asset_uri)
        return [
            pystac.Item(
                collection="test-collection",
                id=Path(asset_uri).stem,
                geometry={
                    "type": "Polygon",
                    "coordinates": [[[0, 0], [0, 1], [1, 1], [0, 0]]],
                },
                bbox=[0, 0, 1, 1],
                datetime=datetime.utcnow(),
                properties=storage.read_json(path),
            )
        ]
