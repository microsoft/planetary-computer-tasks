from pathlib import Path

from pctasks.core.storage.local import LocalStorage

HERE = Path(__file__).parent


def test_walk_with_depth():
    storage = LocalStorage(HERE / ".." / "data-files" / "simple-assets")
    subdirs = {root: files for root, _, files in storage.walk(min_depth=1, max_depth=1)}
    assert list(subdirs.keys()) == ["a", "b"]
    assert set(subdirs["a"]) == set(["asset-a-1.json", "asset-a-2.json"])


def test_walk_folders():
    storage = LocalStorage(HERE / ".." / "data-files" / "simple-assets")
    subdirs = {root: files for root, _, files in storage.walk()}
    assert list(subdirs.keys()) == [".", "a", "b"]
    assert set(subdirs["a"]) == set(["asset-a-1.json", "asset-a-2.json"])


def test_list_files():
    storage = LocalStorage(HERE / ".." / "data-files" / "simple-assets")
    result = storage.list_files()
    assert set(result) == set(
        ["a/asset-a-1.json", "a/asset-a-2.json", "b/asset-b-1.json", "b/asset-b-2.json"]
    )

    b_storage = LocalStorage(HERE / ".." / "data-files" / "simple-assets" / "b")
    result = b_storage.list_files()
    assert set(result) == set(["asset-b-1.json", "asset-b-2.json"])


def test_fsspec_components():
    storage = LocalStorage(HERE / ".." / "data-files" / "simple-assets")
    assert storage.fsspec_storage_options == {}
    assert storage.fsspec_path("foo/bar.csv") == "file://foo/bar.csv"
