import json
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import List, Union

import pystac
from pystac.utils import str_to_datetime

from pctasks.core.models.task import CompletedTaskResult, WaitTaskResult
from pctasks.core.storage import StorageFactory
from pctasks.core.storage.local import LocalStorage
from pctasks.core.utils.stac import validate_stac
from pctasks.dataset.chunks.models import ChunkInfo
from pctasks.dataset.items.models import CreateItemsOutput
from pctasks.dataset.items.task import CreateItemsInput, CreateItemsTask
from pctasks.dev.test_utils import run_test_task
from pctasks.task.utils import get_task_path

HERE = Path(__file__)
TEST_ASSETS_PATH = HERE.parent.parent / "data-files" / "test-assets"

TEST_ASSET_URIS = [f"/asset{i}.tif" for i in range(10)]

WAIT_URI = "/wait-asset.tif"


def create_mock_item(
    asset_uri: str, storage_factory: StorageFactory
) -> Union[List[pystac.Item], WaitTaskResult]:
    if asset_uri == WAIT_URI:
        return WaitTaskResult()

    item = pystac.Item(
        id=Path(asset_uri).stem,
        geometry={"type": "Polygon", "coordinates": [[[0, 0], [0, 1], [1, 1], [0, 0]]]},
        bbox=[0, 0, 1, 1],
        datetime=str_to_datetime("2020-01-01T00:00:00Z"),
        properties={},
    )
    item.add_asset("data", pystac.Asset(href=asset_uri))
    return [item]


test_create_task = CreateItemsTask(create_mock_item)
TASK_PATH = get_task_path(test_create_task, "test_create_task", module=__name__)


def test_create_items():
    with TemporaryDirectory() as tmp_dir:
        tmp_storage = LocalStorage(tmp_dir)
        chunk_storage = tmp_storage.get_substorage("chunks")
        items_storage = tmp_storage.get_substorage("items")

        chunk_path = "chunk.csv"
        ndjson_path = "items.ndjson"

        chunk_storage.write_text(file_path=chunk_path, text="\n".join(TEST_ASSET_URIS))

        args = CreateItemsInput(
            asset_chunk_info=ChunkInfo(
                uri=chunk_storage.get_uri(chunk_path), chunk_id=chunk_path
            ),
            collection_id="test-collection",
            item_chunkset_uri=items_storage.get_uri(ndjson_path),
        )

        task_result = run_test_task(args.dict(), TASK_PATH)
        assert isinstance(task_result, CompletedTaskResult)

        result = CreateItemsOutput.parse_obj(task_result.output)
        ndjson_uri = result.ndjson_uri
        assert ndjson_uri
        assert Path(ndjson_uri).exists()

        items: List[pystac.Item] = []

        for item_json in items_storage.read_text(ndjson_uri).split("\n"):
            items.append(pystac.Item.from_dict(json.loads(item_json)))

        assert len(items) == len(TEST_ASSET_URIS)
        for item in items:
            validate_stac(item)


def test_wait_for_assets():
    args = CreateItemsInput(
        asset_uri=WAIT_URI,
    )

    task_result = run_test_task(args.dict(), TASK_PATH)
    assert isinstance(task_result, WaitTaskResult)
