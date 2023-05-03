from typing import List, Union

from stactools.msbuildings import stac
import pystac

from pctasks.core.models.task import WaitTaskResult
from pctasks.core.storage import StorageFactory
from pctasks.dataset.collection import Collection


class MSBuildingsCollection(Collection):
    @classmethod
    def create_item(
        cls, asset_uri: str, storage_factory: StorageFactory
    ) -> Union[List[pystac.Item], WaitTaskResult]:
        import azure.identity.aio

        _, path = storage_factory.get_storage_for_file(asset_uri)

        if "quadkey" not in path:
            # The listing isn't quite right. Have to return `[]` for
            # the "Region" folders.
            return []

        item = stac.create_item(
            f"abfs://footprints/{path}",
            asset_extra_fields={
                "table:storage_options": {"account_name": "bingmlbuildings"}
            },
            storage_options={
                "account_name": "bingmlbuildings",
                "credential": azure.identity.aio.DefaultAzureCredential(),
            },
        )
        item.collection_id = "ms-buildings"
        return [item]


if __name__ == "__main__":
    [item] = MSBuildingsCollection.create_item(
        "blob://bingmlbuildings/footprints/delta/2023-04-25/ml-buildings.parquet/RegionName=Abyei/quadkey=122321003",
        StorageFactory(),
    )

    assert item.assets["data"].extra_fields["table:storage_options"] == {
        "account_name": "bingmlbuildings"
    }
    assert item.properties["msbuildings:processing-date"] == "2023-04-25"
