import os
from concurrent.futures import ThreadPoolExecutor
from itertools import islice
from typing import Iterable, List, Optional, Set, Union, cast

from pctasks.core.storage import Storage
from pctasks.core.storage.local import LocalStorage
from pctasks.dataset.chunks.constants import (
    ALL_CHUNK_PREFIX,
    FAILURE_CHUNK_PREFIX,
    SUCCESS_CHUNK_PREFIX,
)


class ChunkSet:
    """ChunkSet represents a set of chunk files in storage.

    A chunk file is a text file where each line represents an
    asset path. That asset path can be the specific target of
    processing, or a token asset that represents a group of
    files to be processed for a single STAC Item.

    Chunksets can be created to represent all Assets in a dataset,
    or for some subset, for example the Assets that have been uploaded
    or modified after a certain date (which is useful for updates
    of datasets based on newly uploaded or changed data).

    Args:
        storage: The Storage for this chunkset.
        chunkset_path: The path under the storage where the chunkset
            resides. If None, the top level of the storage is used.

    """

    def __init__(self, storage: Storage, chunkset_path: Optional[str] = None):
        self._chunkset_path = chunkset_path
        self._storage = storage
        self._all_storage = storage.get_substorage(ALL_CHUNK_PREFIX)
        self._success_storage = storage.get_substorage(SUCCESS_CHUNK_PREFIX)
        self._failure_storage = storage.get_substorage(FAILURE_CHUNK_PREFIX)

        self._all_chunks: Optional[Set[str]] = None
        self._success_chunks: Optional[Set[str]] = None
        self._failure_chunks: Optional[Set[str]] = None

    @property
    def chunkset_uri(self) -> str:
        return self._storage.get_uri()

    def get_all_chunks(self, limit: Optional[int] = None) -> Set[str]:
        if limit:
            return set(islice(self._all_storage.list_files(), limit))
        else:
            if self._all_chunks is None:
                self._all_chunks = set(self._all_storage.list_files())

            return self._all_chunks

    @property
    def all_chunks(self) -> Set[str]:
        return self.get_all_chunks()

    @property
    def success_chunks(self) -> Set[str]:
        self._success_chunks = set(self._success_storage.list_files())
        return self._success_chunks

    @property
    def failure_chunks(self) -> Set[str]:
        if self._failure_chunks is None:
            self._failure_chunks = set(self._failure_storage.list_files())
        return self._failure_chunks

    @property
    def unprocessed_chunks(self) -> Set[str]:
        return self.all_chunks - self.success_chunks

    def get_chunk_name(self, chunk_id: str) -> str:
        return chunk_id.replace("/", "-")

    def get_chunk_uri(self, chunk_id: str) -> str:
        return self._all_storage.get_uri(chunk_id)

    def read_chunk(self, chunk_id: str) -> Iterable[str]:
        return self._all_storage.read_text(chunk_id).split("\n")

    def download_chunk(self, chunk_id: str, path: str) -> str:
        target_path = os.path.join(path, ALL_CHUNK_PREFIX, chunk_id)
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        self._all_storage.download_file(chunk_id, target_path)
        return target_path

    def local_copy(self, path: str, threads: Optional[int] = None) -> "ChunkSet":
        """Download all chunks to a directory and
        return the list of chunk IDs. Does not copy success
        and failure chunks.

        threads - Number of threads to use. Default to CPU count
        """

        def copy_chunk(chunk_id: str) -> None:
            target_path = os.path.join(path, ALL_CHUNK_PREFIX, chunk_id)
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            self._all_storage.download_file(chunk_id, target_path)

        with ThreadPoolExecutor(threads or os.cpu_count()) as executor:
            executor.map(copy_chunk, self.all_chunks)

        return ChunkSet(LocalStorage(path))

    def write_chunk(self, chunk_id: str, lines: Union[List[str], List[bytes]]) -> None:
        if len(lines) > 0:
            if type(lines[0]) is str:
                self._all_storage.write_text(
                    chunk_id, "\n".join(cast(List[str], lines))
                )
            else:
                self._all_storage.write_bytes(
                    chunk_id, b"\n".join(cast(List[bytes], lines))
                )

    def mark_success(self, chunk_id: str) -> None:
        """Marks a chunk file as succeeded"""
        self._success_storage.write_text(
            chunk_id, self._all_storage.read_text(chunk_id)
        )

    def mark_failure(self, chunk_id: str) -> None:
        """Marks a chunk file as failed"""
        self._failure_storage.write_text(
            chunk_id, self._all_storage.read_text(chunk_id)
        )

    def clear_cache(self) -> None:
        """Resets the cached chunk lists"""
        self._all_chunks = None
        self._success_chunks = None
        self._failure_chunks = None
