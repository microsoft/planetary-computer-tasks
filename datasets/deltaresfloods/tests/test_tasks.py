import logging
from pathlib import Path

from pctasks.cli.cli import setup_logging
from pctasks.dataset.models import BlobStorageConfig, CollectionConfig, DatasetConfig
from pctasks.core.storage import StorageFactory
from pctasks.core.tokens import Tokens
from pctasks.dataset.splits.models import (
    CreateSplitsOptions,
)
from pctasks.dataset.template import template_dataset_file
from pctasks.task.context import TaskContext
from pctasks.run.workflow.simple import SimpleWorkflowRunner
from pctasks.dataset.workflow import create_chunks_workflow, create_process_items_workflow
import pytest


TESTS_DIR = Path(__file__).parent
DATASET_PATH = TESTS_DIR.parent / "dataset.yaml"


@pytest.fixture
def dataset_config() -> DatasetConfig:
    test_prefix = "test_prefix"
    ds_config = template_dataset_file(DATASET_PATH)
    ds_config.image = "mock:latest"
    ds_config.args = [test_prefix]
    ds_config.collections[0].asset_storage[0].chunks.options.chunk_length = 2
    ds_config.collections[0].chunk_storage = BlobStorageConfig(
        storage_account="devstoreaccount1",
        container="test-data",
        prefix=f"{test_prefix}/chunks",
    )

    ds_config.environment.clear()

    return ds_config


def test_create_chunks(dataset_config) -> None:
    setup_logging(logging.DEBUG)

    collection_config: CollectionConfig = dataset_config.collections[0]
    workflow = create_chunks_workflow(
        dataset=dataset_config,
        collection=collection_config,
        chunkset_id="test",
        create_splits_options=CreateSplitsOptions(limit=10),
    )

    tokens = Tokens(collection_config.get_tokens())
    context = TaskContext(StorageFactory(tokens=tokens))

    runner = SimpleWorkflowRunner()
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
