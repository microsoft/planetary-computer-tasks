import os
from pathlib import Path
from typing import Dict, List, Tuple

import pytest

from pctasks.core.storage.blob import maybe_rewrite_blob_storage_url
from pctasks.dev.blob import temp_azurite_blob_storage
from pctasks.dev.constants import AZURITE_ACCOUNT_NAME, TEST_DATA_CONTAINER

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


def test_fsspec_components():
    with temp_azurite_blob_storage(
        HERE / ".." / "data-files" / "simple-assets"
    ) as storage:
        assert storage.fsspec_storage_options == {"account_name": AZURITE_ACCOUNT_NAME}
        assert (
            storage.fsspec_path("foo/bar.csv")
            == f"abfs://{TEST_DATA_CONTAINER}/foo/bar.csv"
        )


def test_blob_download_timeout():
    TIMEOUT_SECONDS = 5
    with temp_azurite_blob_storage(
        HERE / ".." / "data-files" / "simple-assets"
    ) as storage:
        with storage._get_client() as client:
            with client.container.get_blob_client(
                storage._add_prefix("a/asset-a-1.json")
            ) as blob:
                storage_stream_downloader = blob.download_blob(timeout=TIMEOUT_SECONDS)
                assert (
                    storage_stream_downloader._request_options["timeout"]
                    == TIMEOUT_SECONDS
                )

                storage_stream_downloader = blob.download_blob()
                assert (
                    storage_stream_downloader._request_options.pop("timeout", None)
                    is None
                )


@pytest.mark.parametrize(
    "url, expected",
    [
        (
            "https://example.blob.core.windows.net/container/path/file.txt",
            "blob://example/container/path/file.txt",
        ),
        (
            "https://azurite:10000/devstoreaccount1/container/path/file.txt",
            "blob://devstoreaccount1/container/path/file.txt",
        ),
        (
            "https://localhost:10000/devstoreaccount1/container/path/file.txt",
            "blob://devstoreaccount1/container/path/file.txt",
        ),
        ("path/file.txt", "path/file.txt"),
    ],
)
def test_maybe_rewrite_blob_storage_url(url, expected):
    result = maybe_rewrite_blob_storage_url(url)
    assert result == expected
