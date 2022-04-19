import os
from pathlib import Path
from typing import Dict, List, Tuple

import pytest

from pctasks.dev.blob import async_temp_azurite_blob_storage

HERE = Path(__file__).parent


@pytest.mark.asyncio
async def test_walk():
    async with async_temp_azurite_blob_storage(
        HERE / ".." / "data-files" / "simple-assets"
    ) as storage:

        result: Dict[str, Tuple[List[str], List[str]]] = {}
        async for root, folders, files in storage.walk():
            result[root] = (folders, files)

        assert set(result.keys()) == {".", "a", "b"}
        assert set(result["."][0]) == {"a", "b"}
        assert set(result["a"][1]) == {"asset-a-1.json", "asset-a-2.json"}
        assert set(result["b"][1]) == {"asset-b-1.json", "asset-b-2.json"}


@pytest.mark.asyncio
async def test_list_files():
    async with async_temp_azurite_blob_storage(
        HERE / ".." / "data-files" / "simple-assets"
    ) as storage:
        result = []
        async for item in storage.list_files():
            result.append(item)
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
        async for item in b_storage.list_files():
            result.append(item)

        assert set(result) == set(["asset-b-1.json", "asset-b-2.json"])


@pytest.mark.asyncio
async def test_walk_files():
    async with async_temp_azurite_blob_storage(
        HERE / ".." / "data-files" / "simple-assets"
    ) as storage:
        result = []
        async for root, _, files in storage.walk():
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
        async for root, _, files in b_storage.walk():
            result.extend(files)
        assert set(result) == set(["asset-b-1.json", "asset-b-2.json"])

        result = []
        async for root, _, files in storage.walk(name_starts_with="b"):
            result.extend(files)
        assert set(result) == set(["asset-b-1.json", "asset-b-2.json"])
