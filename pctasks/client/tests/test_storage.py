from pathlib import Path
from tempfile import TemporaryDirectory

from pctasks.dev.blob import temp_azurite_blob_storage
from pctasks.dev.test_utils import run_pctasks

TEST_DATA_DIR = Path(__file__).parent / "data-files"


def test_get():
    with temp_azurite_blob_storage(test_files=TEST_DATA_DIR):
        local_path = TEST_DATA_DIR / "test_collection.json"
        with TemporaryDirectory() as tmp_dir:
            run_pctasks(["storage", "get", str(local_path), "-o", tmp_dir])
            assert (Path(tmp_dir) / "test_collection.json").exists()


def test_put():
    with temp_azurite_blob_storage() as storage:
        local_path = TEST_DATA_DIR / "test_collection.json"
        remote_uri = storage.get_uri() + "/"
        run_pctasks(["storage", "put", str(local_path), remote_uri])

        assert storage.file_exists("test_collection.json")
