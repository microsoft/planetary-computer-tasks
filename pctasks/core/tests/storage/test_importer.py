import importlib.metadata
import textwrap
from pathlib import Path

from pctasks.dev.blob import temp_azurite_blob_storage
from pctasks.core.importer import ensure_code

TESTS = Path(__file__).parent.parent


def test_import_module():
    src = textwrap.dedent("""\
    class Foo:
        def f(self, x):
            return x
    """)

    with temp_azurite_blob_storage() as storage:
        storage.upload_bytes(src.encode(), "mymodule.py")

        ensure_code("mymodule.py", storage)

        cls = importlib.metadata.EntryPoint("", "mymodule:Foo", "").load()
        instance = cls()
        result = instance.f(2)
        assert result == 2


def test_import_package():
    import zipfile
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        path = f"{td}/package.zip"
        with zipfile.PyZipFile(path, "w") as zf:
            zf.writepy(TESTS / "data-files/example_module")

        with temp_azurite_blob_storage() as storage:
            storage.upload_file(path, "mymodule.zip")

            ensure_code("mymodule.zip", storage)

            cls = importlib.metadata.EntryPoint("", "example_module:B", "").load()
            instance = cls()
            assert instance.a() == "a"
            assert instance.b() == "b"
