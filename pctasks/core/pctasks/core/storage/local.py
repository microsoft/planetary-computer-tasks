import logging
import os
import shutil
from datetime import datetime as Datetime
from pathlib import Path
from typing import IO, Any, Generator, Iterable, List, Optional, Tuple, Union

from pctasks.core.storage.base import Storage, StorageFileInfo
from pctasks.core.storage.path_filter import PathFilter

logger = logging.getLogger(__name__)


class LocalStorage(Storage):
    """Storage representing a local directory.

    See Storage for docstrings.
    """

    def __init__(self, base_path: Union[Path, str]):
        # If base_path is a file, use the parent directory
        base_path = str(Path(base_path))
        base_path_dir = base_path
        if os.path.exists(base_path):
            if not os.path.isdir(base_path):
                base_path_dir = os.path.dirname(base_path)
        else:
            if not base_path.endswith("/"):
                # Assume base names with extensions are files.
                if os.path.splitext(base_path)[1]:
                    base_path_dir = os.path.dirname(base_path)
        self.base_dir = os.path.abspath(base_path_dir)

        logger.debug(f"Created local storage: {self}")

    def ensure_dirs(self, path: str, is_dir: bool = False) -> None:
        """Ensures directories exists. Call with either a file_path or folder_path"""
        if is_dir:
            dir_path = os.path.join(self.base_dir, path)
        else:
            dir_path = os.path.join(self.base_dir, os.path.dirname(path))

        os.makedirs(dir_path, exist_ok=True)

    def list_files(
        self,
        name_starts_with: Optional[str] = None,
        since_date: Optional[Datetime] = None,
        extensions: Optional[List[str]] = None,
        ends_with: Optional[str] = None,
        matches: Optional[str] = None,
    ) -> Iterable[str]:
        logger.debug(f"Walking {self.base_dir}")
        result: List[str] = []
        path_filter = PathFilter(
            extensions=extensions, ends_with=ends_with, matches=matches
        )
        for root, _, files in self.walk(
            name_starts_with=name_starts_with,
        ):
            for f in files:
                if path_filter(f):
                    full_path = os.path.join(root, f)
                    full_path = full_path.strip("./")
                    if since_date:
                        if since_date <= Datetime.fromtimestamp(
                            os.path.getmtime(full_path)
                        ):
                            result.append(full_path)
                    else:
                        result.append(full_path)
        return result

    def walk(
        self,
        max_depth: Optional[int] = None,
        min_depth: Optional[int] = None,
        name_starts_with: Optional[str] = None,
        walk_limit: Optional[int] = None,
        file_limit: Optional[int] = None,
    ) -> Generator[Tuple[str, List[str], List[str]], None, None]:
        def _get_depth(path: str) -> int:
            relpath = os.path.relpath(path, self.base_dir)
            if not relpath or relpath == ".":
                return 0
            return len(relpath.strip("/").split("/"))

        walk_count = 0
        file_count = 0
        limit_break = False

        for root, folders, files in os.walk(self.base_dir):
            rel_root = os.path.relpath(root, self.base_dir)

            if name_starts_with and not rel_root.startswith(name_starts_with):
                continue
            depth = _get_depth(root)
            if min_depth and depth < min_depth:
                continue
            if max_depth and depth > max_depth:
                break
            if file_limit and file_count + len(files) > file_limit:
                files = files[: file_limit - file_count]
                limit_break = True
                if not files:
                    break

            yield rel_root, folders, files
            if limit_break:
                break
            walk_count += 1
            if walk_limit and walk_count >= walk_limit:
                break

    def download_file(
        self,
        file_path: str,
        output_path: str,
        is_binary: bool = True,
    ) -> None:
        shutil.copy(os.path.join(self.base_dir, file_path), output_path)

    def file_exists(self, file_path: str) -> bool:
        path = os.path.join(self.base_dir, file_path)
        return os.path.exists(path) and not os.path.isdir(path)

    def get_file_info(self, file_path: str) -> StorageFileInfo:
        path = os.path.join(self.base_dir, file_path)
        file_stats = os.stat(path)
        return StorageFileInfo(size=file_stats.st_size)

    def upload_file(
        self,
        input_path: str,
        target_path: str,
        overwrite: bool = True,
    ) -> None:
        target = os.path.join(self.base_dir, target_path)
        if not os.path.exists(os.path.dirname(target)):
            os.makedirs(os.path.dirname(target))
        if os.path.exists(target) and not overwrite:
            raise FileExistsError(f"{target} already exists.")
        shutil.copy(input_path, target)

    def get_url(self, file_path: str) -> str:
        return f"file://{os.path.join(self.base_dir, file_path)}"

    def get_uri(self, file_path: Optional[str] = None) -> str:
        if file_path is None:
            return self.base_dir
        else:
            return os.path.join(self.base_dir, file_path)

    def get_authenticated_url(self, file_path: str) -> str:
        return self.get_url(file_path)

    def get_path(self, uri: str) -> str:
        return os.path.relpath(uri, self.base_dir)

    def get_substorage(self, path: str) -> "Storage":
        return LocalStorage(os.path.join(self.base_dir, path))

    def open_file(self, file_path: str, mode: str = "r") -> IO[Any]:
        if "w" in mode:
            self.ensure_dirs(file_path)
        return open(os.path.join(self.base_dir, file_path), mode=mode)

    def read_bytes(self, file_path: str) -> bytes:
        with open(os.path.join(self.base_dir, file_path), "rb") as f:
            return f.read()

    def write_bytes(self, file_path: str, data: bytes, overwrite: bool = True) -> None:
        self.ensure_dirs(file_path)
        if not overwrite and self.file_exists(file_path):
            raise FileExistsError(f"{file_path} already exists.")
        with open(os.path.join(self.base_dir, file_path), "wb") as f:
            f.write(data)

    def delete_folder(self, folder_path: str) -> None:
        shutil.rmtree(os.path.join(self.base_dir, folder_path))

    def delete_file(self, file_path: str) -> None:
        os.remove(os.path.join(self.base_dir, file_path))

    def __repr__(self) -> str:
        return f"LocalStorage({self.base_dir})"
