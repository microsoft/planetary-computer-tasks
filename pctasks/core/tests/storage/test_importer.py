import importlib.metadata
import subprocess
import sys
import unittest.mock
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Optional
import zipfile

from pctasks.core.importer import ensure_code, ensure_requirements, write_code
from pctasks.core.storage.blob import BlobStorage
from pctasks.dev.blob import temp_azurite_blob_storage

TESTS = Path(__file__).parent.parent


def _import_module(target_dir: Optional[str] = None):
    path = str(TESTS / "data-files/example_module/a.py")
    with temp_azurite_blob_storage() as storage:
        assert isinstance(storage, BlobStorage)
        uri = storage.upload_code(path)
        token = "b618be31818766973c94818a9e29a8f6"
        assert uri == f"blob://devstoreaccount1/test-data/{storage.prefix}/{token}/a.py"
        p = ensure_code(f"{token}/a.py", storage, target_dir=target_dir)
        if target_dir:
            assert target_dir in sys.path
            assert list(Path(target_dir).glob("a.py"))
        assert p.name == "a.py"

        cls = importlib.metadata.EntryPoint("", "a:A", "").load()
        instance = cls()
        result = instance.a()
        assert result == "a"


def test_import_module():
    _import_module()


def test_import_module_target_dir():
    with TemporaryDirectory() as target_dir:
        try:
            _import_module(target_dir)
        finally:
            if target_dir in sys.path:
                sys.path.remove(target_dir)


def _import_package(target_dir: Optional[str] = None):
    path = str(TESTS / "data-files/example_module")

    with temp_azurite_blob_storage() as storage:
        assert isinstance(storage, BlobStorage)
        uri = storage.upload_code(path)

        assert uri.startswith(f"blob://devstoreaccount1/test-data/{storage.prefix}/")
        assert uri.endswith("/example_module.zip")
        path = storage.get_path(uri)
        result = ensure_code(path, storage, target_dir=target_dir)
        if target_dir:
            assert target_dir in sys.path
            assert list(Path(target_dir).glob("example_module.zip"))
        cls = importlib.metadata.EntryPoint("", "example_module:B", "").load()
        instance = cls()
        assert instance.a() == "a"
        assert instance.b() == "b"
        assert result.name == "example_module.zip"
        assert Path(sys.path[0]).name == "example_module.zip"


def test_import_package():
    _import_package()


def test_import_package_target_dir():
    with TemporaryDirectory() as target_dir:
        try:
            _import_package(target_dir)
        finally:
            if target_dir in sys.path:
                sys.path.remove(target_dir)


def _ensure_requirements(target_dir: Optional[str] = None):
    remote_path = "requirements.txt"
    with temp_azurite_blob_storage() as storage:
        storage.upload_bytes(b"pystac==1.*", remote_path)
        with unittest.mock.patch(
            "pctasks.core.importer.subprocess", autospec=True
        ) as p:
            p.Popen.return_value.communicate.return_value = (b"a", b"b")
            p.Popen.return_value.wait.return_value = 0
            p.CalledProcessError = subprocess.CalledProcessError

            ensure_requirements(
                remote_path, storage, pip_options=["--upgrade"], target_dir=target_dir
            )

            assert p.Popen.call_count


def test_ensure_requirements():
    _ensure_requirements()


def test_ensure_requirements_target_dir():
    with TemporaryDirectory() as target_dir:
        try:
            _ensure_requirements(target_dir)
        finally:
            if target_dir in sys.path:
                sys.path.remove(target_dir)



def test_write_code():
    with TemporaryDirectory() as temp_dir:
        p = Path(temp_dir)
        pkg = p / "my_package"
        module = pkg / "my_file.py"
        module.parent.mkdir(exist_ok=True)
        module.touch()

        name, buf = write_code(pkg)

    assert name == "my_package.zip"

    with zipfile.ZipFile(buf) as zf:
        assert len(zf.filelist) == 1
        assert zf.filelist[0].filename == "my_package/my_file.py"
