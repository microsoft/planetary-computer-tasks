from pathlib import Path
from typing import Dict, List, Tuple

from pctasks.dev.blob import files_in_azurite

HERE = Path(__file__).parent


def test_walk():
    with files_in_azurite(HERE / ".." / "data-files" / "simple-assets") as storage:
        result: Dict[str, Tuple[List[str], List[str]]] = {}
        for root, folders, files in storage.walk():
            result[root] = (folders, files)

        assert set(result.keys()) == {".", "a", "b"}
        assert set(result["."][0]) == {"a", "b"}
        assert set(result["a"][1]) == {"asset-a-1.json", "asset-a-2.json"}
        assert set(result["b"][1]) == {"asset-b-1.json", "asset-b-2.json"}


def test_list_files():
    with files_in_azurite(HERE / ".." / "data-files" / "simple-assets") as storage:
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
