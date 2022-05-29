import json
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
from pctasks.dataset.template import template_dataset_file
from pctasks.dataset.workflow import create_process_items_workflow
from pctasks.dev.blob import (
    copy_dir_to_azurite,
    get_azurite_sas_token,
    temp_azurite_blob_storage,
)
from pctasks.execute.runner.local import LocalRunner
from pctasks.task.context import TaskContext

HERE = Path(__file__).parent
DATASET_PATH = HERE / "data-files/datasets/test-dataset.yaml"


def test_process_items() -> None:
    setup_logging(logging.DEBUG)

    ds_config = template_dataset_file(DATASET_PATH)
    collection_config = ds_config.collections[0]

    workflow = create_process_items_workflow(
        ds_config, collection_config, chunkset_id="test-chunkset", ingest=False
    )

    print(workflow.to_yaml())

    tokens = collection_config.get_tokens()

    with TemporaryDirectory() as tmp_dir:
        with temp_azurite_blob_storage() as storage:
            copy_dir_to_azurite(
                storage, HERE / "data-files" / "simple-assets", prefix="assets"
            )
            path = BlobUri(storage.get_uri()).blob_name
            assert path
            outputs = LocalRunner().run_workflow(
                workflow,
                output_uri=tmp_dir,
                args={"test_prefix": path, "sas_token": get_azurite_sas_token()},
                context=TaskContext(
                    storage_factory=StorageFactory(tokens=Tokens(tokens))
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
                    pystac.Item.from_dict(item).validate()
                    ids.add(item["id"])
            assert len(ids) == 4
