import os
from pathlib import Path
from typing import Dict, List, Tuple

from pctasks.dev.blob import temp_azurite_blob_storage

HERE = Path(__file__).parent


def test_walk():
    with temp_azurite_blob_storage(
        HERE / ".." / "data-files" / "simple-assets"
    ) as storage:

        result: Dict[str, Tuple[List[str], List[str]]] = {}
        for root, folders, files in storage.walk():
            result[root] = (folders, files)

        assert set(result.keys()) == {".", "a", "b"}
        assert set(result["."][0]) == {"a", "b"}
        assert set(result["a"][1]) == {"asset-a-1.json", "asset-a-2.json"}
        assert set(result["b"][1]) == {"asset-b-1.json", "asset-b-2.json"}


def test_list_files():
    with temp_azurite_blob_storage(
        HERE / ".." / "data-files" / "simple-assets"
    ) as storage:
        result = storage.list_files()
        assert set(result) == set(
            [
                "a/asset-a-1.json",
                "a/asset-a-2.json",
                "b/asset-b-1.json",
                "b/asset-b-2.json",
            ]
        )

        b_storage = storage.get_substorage("b")
        result = b_storage.list_files()
        assert set(result) == set(["asset-b-1.json", "asset-b-2.json"])


def test_walk_files():
    with temp_azurite_blob_storage(
        HERE / ".." / "data-files" / "simple-assets"
    ) as storage:
        result = []
        for root, _, files in storage.walk():
            result.extend(os.path.join(root, f) for f in files)
        assert set(result) == set(
            [
                "a/asset-a-1.json",
                "a/asset-a-2.json",
                "b/asset-b-1.json",
                "b/asset-b-2.json",
            ]
        )

        b_storage = storage.get_substorage("b")
        result = []
        for root, _, files in b_storage.walk():
            result.extend(files)
        assert set(result) == set(["asset-b-1.json", "asset-b-2.json"])

        result = []
        for root, _, files in storage.walk(name_starts_with="b"):
            result.extend(files)
        assert set(result) == set(["asset-b-1.json", "asset-b-2.json"])
