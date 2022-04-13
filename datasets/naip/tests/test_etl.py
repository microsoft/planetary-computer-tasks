import logging
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Set

import orjson
import pystac
from pctasks.cli.cli import setup_logging
from pctasks.core.storage import StorageFactory
from pctasks.core.storage.blob import BlobUri
from pctasks.core.tokens import Tokens
from pctasks.dataset.splits.models import CreateSplitsOptions
from pctasks.dataset.template import template_dataset_file
from pctasks.dataset.workflow import ProcessItemsWorkflowConfig
from pctasks.dev.blob import temp_azurite_blob_storage
from pctasks.execute.local import LocalRunner
from pctasks.task.context import TaskContext

HERE = Path(__file__).parent
DATASET_PATH = HERE / "test-dataset.yaml"


def test_process_items() -> None:
    setup_logging(logging.DEBUG)

    ds_config = template_dataset_file(DATASET_PATH)
    collection_config = ds_config.collections[0]

    asset_storage = collection_config.asset_storage[0]
    chunk_options = asset_storage.chunks.options
    assert chunk_options.chunk_length == 3
    chunk_options = chunk_options.copy(update={"limit": 6})

    workflow = ProcessItemsWorkflowConfig.from_collection(
        ds_config,
        collection_config,
        chunkset_id="test-chunkset",
        ingest=False,
        create_splits_options=CreateSplitsOptions(limit=2),
        create_chunks_options=chunk_options,
    )

    print(workflow.to_yaml())

    tokens = collection_config.get_tokens()

    with TemporaryDirectory() as tmp_dir:
        with temp_azurite_blob_storage() as storage:
            path = BlobUri(storage.get_uri()).blob_name
            assert path
            LocalRunner().run_workflow(
                workflow,
                output_uri=tmp_dir,
                args={"test_prefix": path},
                context=TaskContext(
                    storage_factory=StorageFactory(tokens=Tokens(tokens))
                ),
            )

            ndjson_paths = list(
                storage.list_files(
                    name_starts_with="chunks/test-chunkset/items/all",
                    extensions=[".ndjson"],
                )
            )

            # Two splits, 2 chunks per split, 3 items per chunk
            assert len(ndjson_paths) == 4

            ids: Set[str] = set()
            for path in ndjson_paths:
                ndjson = storage.read_text(path)
                lines = ndjson.splitlines()
                assert len(lines) == 3
                for line in lines:
                    item = orjson.loads(line)
                    pystac.Item.from_dict(item).validate()
                    ids.add(item["id"])
            assert len(ids) == 12
