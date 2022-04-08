from pathlib import Path
from tempfile import TemporaryDirectory

from pctasks.core.storage import StorageFactory
from pctasks.core.storage.blob import BlobAccess, BlobUri
from pctasks.dataset.template import template_dataset_file
from pctasks.dataset.workflow import ProcessItemsWorkflowConfig
from pctasks.dev.blob import files_in_azurite, get_azurite_sas_token
from pctasks.execute.local import LocalRunner
from pctasks.task.context import TaskContext

HERE = Path(__file__).parent
DATASET_PATH = HERE / "data-files/datasets/test-dataset.yaml"


def test_process_items():
    ds_config = template_dataset_file(DATASET_PATH)
    collection_config = ds_config.collections[0]

    workflow = ProcessItemsWorkflowConfig.from_collection(
        ds_config,
        collection_config,
        chunkset_id="test-chunkset",
        db_connection_str="${{ secrets.DB_CONNECTION_STRING }}",
    )

    tokens = collection_config.get_tokens()

    with TemporaryDirectory() as tmp_dir:
        with files_in_azurite(HERE / "data-files" / "simple-assets") as storage:
            path = BlobUri(storage.get_uri()).blob_name
            assert path
            LocalRunner().run_workflow(
                workflow,
                output_uri=tmp_dir,
                args={"test_prefix": path, "sas_token": get_azurite_sas_token()},
                context=TaskContext(
                    storage_factory=StorageFactory(blob_access=BlobAccess(tokens))
                ),
            )
