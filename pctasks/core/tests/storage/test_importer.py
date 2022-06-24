import importlib.metadata
from pathlib import Path

from pctasks.core.importer import ensure_code
from pctasks.core.storage.blob import BlobStorage
from pctasks.dev.blob import temp_azurite_blob_storage

TESTS = Path(__file__).parent.parent


def test_import_module():
    path = str(TESTS / "data-files/example_module/a.py")
    with temp_azurite_blob_storage() as storage:
        assert isinstance(storage, BlobStorage)
        uri = storage.upload_code(path)
        token = "b618be31818766973c94818a9e29a8f6"
        assert uri == f"blob://devstoreaccount1/test-data/{storage.prefix}/{token}/a.py"
        p = ensure_code(f"{token}/a.py", storage)
        assert p.name == "a.py"

        cls = importlib.metadata.EntryPoint("", "a:A", "").load()
        instance = cls()
        result = instance.a()
        assert result == "a"


def test_import_package():
    path = str(TESTS / "data-files/example_module")

    with temp_azurite_blob_storage() as storage:
        assert isinstance(storage, BlobStorage)
        uri = storage.upload_code(path)

        assert uri.startswith(f"blob://devstoreaccount1/test-data/{storage.prefix}/")
        assert uri.endswith("/example_module.zip")
        path = storage.get_path(uri)
        result = ensure_code(path, storage)
        cls = importlib.metadata.EntryPoint("", "example_module:B", "").load()
        instance = cls()
        assert instance.a() == "a"
        assert instance.b() == "b"
        assert result.name == "example_module.zip"
