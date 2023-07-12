import datetime
import uuid
from typing import List, Union

import pystac
from pctasks.core.models.task import WaitTaskResult
from pctasks.core.storage import StorageFactory
from pctasks.dataset.collection import Collection


class EchoCollection(Collection):  # type: ignore
    @classmethod
    def create_item(
        cls, asset_uri: str, storage_factory: StorageFactory
    ) -> Union[List[pystac.Item], WaitTaskResult]:
        item = pystac.Item(
            id=str(uuid.uuid4()),
            bbox=[-180, -90, 180, 90],
            geometry={
                "type": "Polygon",
                "coordinates": [
                    [[-180, -90], [-180, 90], [180, 90], [180, -90], [-180, -90]]
                ],
            },
            datetime=datetime.datetime.utcnow(),
            properties={},
            assets={
                "data": pystac.Asset(href=asset_uri),
            },
        )
        return [item]
