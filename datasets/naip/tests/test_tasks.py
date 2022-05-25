import logging
from pathlib import Path

from pctasks.cli.cli import setup_logging
from pctasks.core.models.task import CompletedTaskResult
from pctasks.core.storage import StorageFactory
from pctasks.core.storage.blob import BlobUri
from pctasks.core.tokens import Tokens
from pctasks.core.utils.template import DictTemplater
from pctasks.dataset.chunks.models import ChunksOutput, CreateChunksTaskConfig
from pctasks.dataset.splits.models import (
    CreateSplitsOptions,
    CreateSplitsOutput,
    CreateSplitsTaskConfig,
)
from pctasks.dataset.template import template_dataset_file
from pctasks.dev.blob import temp_azurite_blob_storage
from pctasks.execute.runner.local import LocalRunner
from pctasks.task.context import TaskContext

HERE = Path(__file__).parent
DATASET_PATH = HERE / "test-dataset.yaml"


def test_create_splits() -> None:
    setup_logging(logging.DEBUG)

    ds_config = template_dataset_file(DATASET_PATH)
    collection_config = ds_config.collections[0]
    tokens = Tokens(collection_config.get_tokens())

    task = CreateSplitsTaskConfig.from_collection(
        ds_config, collection_config, options=CreateSplitsOptions(limit=2)
    )

    result = LocalRunner().run_task(task, TaskContext(StorageFactory(tokens=tokens)))
    print(result.to_yaml())
    assert isinstance(result, CompletedTaskResult)
    output = CreateSplitsOutput.parse_obj(result.output)

    assert len(output.splits) == 2


def test_create_chunks() -> None:
    setup_logging(logging.DEBUG)

    ds_config = template_dataset_file(DATASET_PATH)
    collection_config = ds_config.collections[0]
    tokens = Tokens(collection_config.get_tokens())

    with temp_azurite_blob_storage() as storage:
        path = BlobUri(storage.get_uri()).blob_name
        assert path

        asset_storage = collection_config.asset_storage[0]
        chunk_options = asset_storage.chunks.options

        assert chunk_options.extensions == [".tif"]
        assert chunk_options.chunk_length == 3
        chunk_options = chunk_options.copy(update={"limit": 6})

        task = CreateChunksTaskConfig.from_collection(
            ds_config,
            collection_config,
            "test-chunkset",
            "blob://naipeuwest/naip/v002/al/",
            options=chunk_options,
        )

        task = DictTemplater(
            {"args": {"test_prefix": path}}, strict=False
        ).template_model(task)

        result = LocalRunner().run_task(
            task, TaskContext(StorageFactory(tokens=tokens))
        )
        print(result.to_yaml())
        assert isinstance(result, CompletedTaskResult)
        output = ChunksOutput.parse_obj(result.output)

        for chunk in output.chunks:
            path = storage.get_path(chunk.uri)
            print("CHUNK PATH:", path)
            print(storage.read_text(path))

        assert len(output.chunks) == 2
        for chunk in output.chunks:
            for line in storage.read_text(storage.get_path(chunk.uri)).splitlines():
                print(line)
                assert line.endswith(".tif")
