import json
import logging
from pathlib import Path

import pytest

from pctasks.cli.cli import setup_logging
from pctasks.core.storage import StorageFactory
from pctasks.core.tokens import Tokens
from pctasks.dataset.items.models import CreateItemsOptions
from pctasks.dataset.models import (
    ChunkOptions,
    CollectionDefinition,
    DatasetDefinition,
    StorageDefinition,
)
from pctasks.dataset.splits.models import CreateSplitsOptions
from pctasks.dataset.template import template_dataset_file
from pctasks.dataset.workflow import (
    create_chunks_workflow,
    create_process_items_workflow,
)
from pctasks.run.workflow.executor.simple import SimpleWorkflowExecutor
from pctasks.task.context import TaskContext

TESTS_DIR = Path(__file__).parent
DATASET_PATH = TESTS_DIR.parent / "dataset.yaml"


@pytest.fixture
def dataset_config() -> DatasetDefinition:
    test_prefix = "test_prefix"
    ds_config = template_dataset_file(DATASET_PATH)
    ds_config.image = "mock:latest"
    ds_config.args = [test_prefix]
    ds_config.collections[0].asset_storage[0].chunks.options.chunk_length = 2
    ds_config.collections[0].chunk_storage = StorageDefinition(
        uri=f"blob://devstoreaccount1/test-data/{test_prefix}/chunks",
    )

    if ds_config.environment:
        ds_config.environment.clear()

    return ds_config


def test_create_chunks(dataset_config: DatasetDefinition) -> None:
    collection_config: CollectionDefinition = dataset_config.collections[0]
    workflow = create_chunks_workflow(
        dataset=dataset_config,
        collection=collection_config,
        chunkset_id="test",
        create_splits_options=CreateSplitsOptions(limit=10),
    )

    tokens = Tokens(collection_config.get_tokens())
    context = TaskContext(StorageFactory(tokens=tokens), run_id="test-1")

    runner = SimpleWorkflowExecutor()
    result = runner.run_workflow(
        workflow, context=context, args={"test_prefix": "test"}
    )
    chunk_uri = result["create-chunks"]["tasks"]["create-chunks"]["output"]["chunks"][
        0
    ]["uri"]
    storage, blob = context.storage_factory.get_storage_for_file(chunk_uri)
    chunklines = storage.read_text(blob).split("\n")
    assert (
        chunklines[0]
        == "blob://deltaresfloodssa/floods-stac/floods/LIDAR-5km-2018-0000.json"
    )


def test_create_items(dataset_config: DatasetDefinition) -> None:
    setup_logging(logging.DEBUG)

    collection_config: CollectionDefinition = dataset_config.collections[0]
    tokens = Tokens(collection_config.get_tokens())
    context = TaskContext(StorageFactory(tokens=tokens), run_id="test-1")

    runner = SimpleWorkflowExecutor()

    workflow = create_process_items_workflow(
        dataset=dataset_config,
        collection=collection_config,
        chunkset_id="test",
        ingest=False,
        create_splits_options=CreateSplitsOptions(limit=1),
        chunk_options=ChunkOptions(limit=2, chunk_length=2),
        create_items_options=CreateItemsOptions(limit=2),
    )

    result = runner.run_workflow(
        workflow, context=context, args={"test_prefix": "test"}
    )
    chunk_uri = result["process-chunk"]["tasks"]["create-items"]["output"]["ndjson_uri"]
    storage, blob = context.storage_factory.get_storage_for_file(chunk_uri)
    ndjson_lines = storage.read_text(blob).split("\n")
    items = [json.loads(text) for text in ndjson_lines]
    assert items[0]["collection"] == "deltares-floods"
