import json
import logging
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Set

import orjson
import pytest

from pctasks.cli.cli import setup_logging
from pctasks.core.storage import StorageFactory
from pctasks.core.storage.blob import BlobUri
from pctasks.core.tokens import Tokens
from pctasks.core.utils.stac import validate_stac
from pctasks.dataset.template import template_dataset_file
from pctasks.dataset.workflow import create_process_items_workflow
from pctasks.dev.blob import (
    copy_dir_to_azurite,
    get_azurite_sas_token,
    temp_azurite_blob_storage,
)
from pctasks.run.workflow.executor.simple import SimpleWorkflowExecutor
from pctasks.task.context import TaskContext

HERE = Path(__file__).parent
DATASET_PATH = HERE / "data-files/datasets/test-dataset.yaml"


def test_process_items() -> None:
    setup_logging(logging.DEBUG)

    ds_config = template_dataset_file(DATASET_PATH)
    collection_config = ds_config.collections[0]

    with TemporaryDirectory() as tmp_dir:
        with temp_azurite_blob_storage() as storage:
            # Run this twice, once from scratch and once with the
            # chunkset from the first loop
            for use_existing_chunks in [False, True]:
                workflow = create_process_items_workflow(
                    ds_config,
                    collection_config,
                    chunkset_id="test-chunkset",
                    ingest=False,
                    target="test",
                    use_existing_chunks=use_existing_chunks,
                )
                assert workflow.target_environment == "test"

                print(workflow.to_yaml())

                tokens = collection_config.get_tokens()

                copy_dir_to_azurite(
                    storage, HERE / "data-files" / "simple-assets", prefix="assets"
                )
                path = BlobUri(storage.get_uri()).blob_name
                assert path
                outputs = SimpleWorkflowExecutor().run_workflow(
                    workflow,
                    output_uri=tmp_dir,
                    args={"test_prefix": path, "sas_token": get_azurite_sas_token()},
                    context=TaskContext(
                        storage_factory=StorageFactory(tokens=Tokens(tokens)),
                        run_id="test-dataset-1",
                    ),
                )

                print(json.dumps(outputs, indent=2))

                ndjson_paths = list(
                    storage.list_files(
                        name_starts_with="chunks/test-chunkset/items/all",
                        extensions=[".ndjson"],
                    )
                )

                assert len(ndjson_paths) == 2

                ids: Set[str] = set()
                for path in ndjson_paths:
                    ndjson = storage.read_text(path)
                    lines = ndjson.splitlines()
                    assert len(lines) == 2
                    for line in lines:
                        item = orjson.loads(line)
                        validate_stac(item)
                        ids.add(item["id"])
                assert len(ids) == 4


@pytest.mark.parametrize("has_args", [True, False])
def test_process_items_is_update_workflow(has_args) -> None:
    ds_config = template_dataset_file(DATASET_PATH)
    if not has_args:
        ds_config = ds_config.copy(update={"args": None})
        assert ds_config.args is None

    collection_config = ds_config.collections[0]

    workflow = create_process_items_workflow(
        ds_config,
        collection_config,
        chunkset_id="${{ args.since }}",
        ingest=False,
        target="test",
        is_update_workflow=True,
    )
    assert "since" in workflow.args
    assert (
        workflow.jobs["create-splits"]
        .tasks[0]
        .args["inputs"][0]["chunk_options"]["since"]
        == "${{ args.since }}"
    )


def test_task_config_tags() -> None:
    ds_config = template_dataset_file(DATASET_PATH)
    assert (
        ds_config.task_config["test-dataset"]["create-items"]["tags"]["batch_pool_id"]
        == "high_memory_pool"
    )
    assert (
        ds_config.task_config["test-dataset"]["ingest-collection"]["tags"]["batch_pool_id"]
        == "ingest_pool"
    )

    collection_config = ds_config.collections[0]

    workflow = create_process_items_workflow(
        ds_config,
        collection_config,
        chunkset_id="test",
        tags={"tag": "value", "batch_pool_id": "overwritten"},
    )

    assert workflow.jobs["process-chunk"].tasks[0].tags["tag"] == "value"
    assert (
        workflow.jobs["process-chunk"].tasks[0].tags["batch_pool_id"]
        == "high_memory_pool"
    )
