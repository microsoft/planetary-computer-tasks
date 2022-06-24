import json
import os
from pathlib import Path
from uuid import uuid1

from pctasks.dataset.template import template_dataset_file
from pctasks.dataset.workflow import create_process_items_workflow
from pctasks.dev.blob import copy_dir_to_azurite, temp_azurite_blob_storage
from pctasks.dev.db import temp_pgstac_db
from pctasks.dev.test_utils import (
    assert_workflow_is_successful,
    run_workflow,
    run_workflow_from_file,
)
from pctasks.ingest.constants import DB_CONNECTION_STRING_ENV_VALUE

HERE = Path(__file__).parent
DATASETS = HERE
TEST_DATA = HERE / ".." / "data-files"
WORKFLOWS = HERE / ".." / "workflows"

TIMEOUT_SECONDS = 180


def test_dataset():
    with temp_pgstac_db(os.environ["SECRETS_DB_CONNECTION_STRING"]) as conn_str:
        test_tag = uuid1().hex[:5]
        collection_id = f"test-collection-{test_tag}"

        # Ingest collection

        collection_path = HERE / ".." / "data-files" / "collection.json"
        with collection_path.open() as f:
            collection = json.load(f)
        collection["id"] = collection_id
        collection_run_id = run_workflow_from_file(
            WORKFLOWS / "ingest-collection.yaml",
            args={"collection": collection, "db_connection_str": conn_str},
        )
        assert_workflow_is_successful(
            collection_run_id, timeout_seconds=TIMEOUT_SECONDS
        )

        # Process items

        dataset = template_dataset_file(HERE / "dataset.yaml")
        if not dataset.environment:
            dataset.environment = {}
        dataset.environment[DB_CONNECTION_STRING_ENV_VALUE] = conn_str
        workflow = create_process_items_workflow(
            dataset,
            dataset.collections[0],
            chunkset_id="test-" + test_tag,
        )

        with temp_azurite_blob_storage() as root_storage:
            assets_storage = root_storage.get_substorage(f"{collection_id}/assets")
            chunks_storage = root_storage.get_substorage("chunks")
            items_storage = root_storage.get_substorage("items")

            copy_dir_to_azurite(assets_storage, TEST_DATA / "assets")

            run_id = run_workflow(
                workflow,
                args={
                    "collection_id": collection_id,
                    "assets_uri": assets_storage.get_uri(),
                    "chunks_uri": chunks_storage.get_uri(),
                    "items_uri": items_storage.get_uri(),
                    "code_path": str(HERE.resolve()),
                },
            )

            assert_workflow_is_successful(run_id, timeout_seconds=TIMEOUT_SECONDS)

        # Check items
