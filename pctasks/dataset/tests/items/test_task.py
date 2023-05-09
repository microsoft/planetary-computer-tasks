import json
import logging
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import List, Union

import pystac
import pytest
import responses
from pystac.utils import str_to_datetime

import pctasks.dataset.items.task
from pctasks.core.models.task import CompletedTaskResult, WaitTaskResult
from pctasks.core.storage import StorageFactory
from pctasks.core.storage.local import LocalStorage
from pctasks.core.utils.stac import validate_stac
from pctasks.dataset.chunks.models import ChunkInfo
from pctasks.dataset.items.models import CreateItemsOutput
from pctasks.dataset.items.task import (
    CreateItemsError,
    CreateItemsInput,
    CreateItemsTask,
    traced_create_item,
    validate_create_items_result,
    validate_item,
)
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


def test_validate_item_sets_collection_id():
    (item,) = create_mock_item(asset_uri="test.tif", storage_factory=None)
    result = validate_item(item, collection_id="test-collection")
    assert result.collection_id == "test-collection"


def test_validate_item_with_collection_id():
    (item,) = create_mock_item(asset_uri="test.tif", storage_factory=None)
    item.collection_id = "test-collection"
    result = validate_item(item, collection_id=None)
    assert result.collection_id == "test-collection"


def test_validate_item_mismatching_collection_id_raises():
    (item,) = create_mock_item(asset_uri="test.tif", storage_factory=None)
    item.collection_id = "test-collection"

    with pytest.raises(
        CreateItemsError,
        match="Item test has collection test-collection but expected other-collection",
    ):
        validate_item(item, collection_id="other-collection")


def test_validate_item_missing_collection_id_raises():
    (item,) = create_mock_item(asset_uri="test.tif", storage_factory=None)
    with pytest.raises(CreateItemsError, match="Item test has no collection ID"):
        validate_item(item, collection_id=None)


def test_validate_item_validates_item():
    (item,) = create_mock_item(asset_uri="test.tif", storage_factory=None)
    item.datetime = None
    # this is not valid

    with pytest.raises(pystac.errors.STACError):
        validate_item(item, collection_id="test-collection")


def test_validate_create_items_result():
    result = create_mock_item(asset_uri="test.tif", storage_factory=None)
    validate_create_items_result(result, collection_id="test-collection")


def test_validate_create_items_raises():
    result = create_mock_item(asset_uri="test.tif", storage_factory=None)
    with pytest.raises(CreateItemsError):
        validate_create_items_result(result, collection_id=None)

    validate_create_items_result(result, collection_id=None, skip_validation=True)


@responses.activate
def test_log_to_monitor(monkeypatch, caplog):
    monkeypatch.setenv(
        "APPLICATIONINSIGHTS_CONNECTION_STRING",
        "InstrumentationKey=00000000-0000-0000-0000-000000000000;IngestionEndpoint=https://westeurope-5.in.applicationinsights.azure.com/;LiveEndpoint=https://westeurope.livediagnostics.monitor.azure.com/",  # noqa: E501
    )
    # opencensus will log an error about the instrumentation key being invalid
    opencensus_logger = logging.getLogger("opencensus.ext.azure")
    opencensus_logger.setLevel(logging.CRITICAL)

    responses.post(
        "https://westus-0.in.applicationinsights.azure.com//v2.1/track",
    )

    # Ensure that any previous tests initializing logging
    # (without an instrumentation key) didn't mess up our handler
    monkeypatch.setattr(pctasks.dataset.items.task, "azhandler", None)

    with caplog.at_level(logging.INFO):
        with traced_create_item("blob://test/test/asset.tif", "test-collection"):
            pass

        record = caplog.records[1]
        assert record.custom_dimensions.pop("duration_seconds")
        assert record.custom_dimensions == {
            "asset_uri": "blob://test/test/asset.tif",
            "collection_id": "test-collection",
            "type": "pctasks.create_item",
        }

    azlogger = logging.getLogger("monitor.pctasks.dataset.items.task")
    assert len(azlogger.handlers) == 1
