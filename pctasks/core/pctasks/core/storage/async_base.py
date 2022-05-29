import logging
from abc import ABC, abstractmethod
from datetime import datetime as Datetime
from typing import Any, AsyncGenerator, AsyncIterable, Dict, List, Optional, Tuple

import orjson

from pctasks.core.storage.base import StorageFileInfo

logger = logging.getLogger(__name__)


class AsyncStorage(ABC):
    """Abstraction over storage.

    Represents storage that is scoped to a storage base, which
    may be a directory, a storage account and container, a
    storage account, container, and a prefix, etc.

    Some termnonology Storage uses:
      path - A path relative to the storage base
      url - The http(s) URL for a path (to be renamed to href)
      uri - A resource ID that can use non-http schemes;
        e.g. a etlcommon.storage.blob.BlobUri like
        "blob://storage_account/container/prefix/blob.txt"

    """

    @abstractmethod
    async def list_files(
        self,
        name_starts_with: Optional[str] = None,
        since_date: Optional[Datetime] = None,
        extensions: Optional[List[str]] = None,
        ends_with: Optional[str] = None,
        matches: Optional[str] = None,
    ) -> AsyncIterable[str]:
        """List file names.

        Args:
            name_starts_with (str): Optional prefix to filter
                file paths by.
            since_date: Optional datetime to filter files by;
                only files with a modified time after this date
                will be included.
            extensions: Optional list of extensions that path must have.
            ends_with: Optional string that path must end with
            matches: Optional regex that path must match

        Returns:
            Iterator of file paths.
        """
        pass

    @abstractmethod
    async def walk(
        self,
        max_depth: Optional[int] = None,
        min_depth: Optional[int] = None,
        name_starts_with: Optional[str] = None,
        since_date: Optional[Datetime] = None,
        extensions: Optional[List[str]] = None,
        ends_with: Optional[str] = None,
        matches: Optional[str] = None,
        walk_limit: Optional[int] = None,
        file_limit: Optional[int] = None,
    ) -> AsyncGenerator[Tuple[str, List[str], List[str]], None]:
        """
        Recursively walk storage.

        Args:
            max_depth: Maximum depth of folders to walk. None will walk all folders.
            min_depth: Minimum depth of folders to record values at.
                None will store records at all depths up to max_depth if specified.
            name_starts_with: Only walk folders and files matching this prefix.
            since_date: Only walk files that have been modified at or after this datetime.
            extensions: Optional list of extensions that file path must have.
            ends_with: Optional string that files must end with
            matches: Optional regex that path must match
            walk_limit: Limit the number of times to yield
            file_limit: Limit the number of files returned

        Returns:
            Generator of (path, files, folders) tuples. Similar to os.walk. Lists
            folders in order of hierarchy, so all subfolders with depth 1 returned first,
            all subfolders with depth 2 returned second, etc.

        """  # noqa
        pass

    @abstractmethod
    async def download_file(
        self,
        file_path: str,
        output_path: str,
        is_binary: bool = True,
    ) -> None:
        """Downloads a file to a local file.

        Args:
            file_path (str): Path to the file.
            output_path (str): The local file location to download to.
            is_binary (bool): True if this is a binary file; use False to
                write the file in text mode. Defaults to True.
        """
        pass

    @abstractmethod
    async def file_exists(self, file_path: str) -> bool:
        """Returns True if a file exists."""
        pass

    @abstractmethod
    async def get_file_info(self, file_path: str) -> StorageFileInfo:
        """Returns information for a file at the given path"""
        pass

    @abstractmethod
    async def upload_file(
        self,
        input_path: str,
        target_path: str,
        overwrite: bool = True,
    ) -> None:
        """Upload a local file to a storage file.

        Args:
            input_path (str): The local path to the file to be uploaded.
            target_path (str): Name target storage path.
            overwrite (bool): Ovewrite existing files. Defaults to True.
        """
        pass

    @abstractmethod
    def get_url(self, file_path: str) -> str:
        """Gets the http url of a file path.

        Args:
            file_path (str): Path of the file.

        Returns:
            str: The URL of the file
        """
        pass

    @abstractmethod
    async def get_uri(self, file_path: Optional[str] = None) -> str:
        """Returns the URI for a file at the file path, or the storage URI if
        no file path is given."""
        pass

    @abstractmethod
    async def get_authenticated_url(self, file_path: str) -> str:
        """Gets a URL with authentication information.

        Raises an exception authentication is not available and
        is required.

        Returns:
            str: The authenticated URL
        """
        pass

    @abstractmethod
    def get_path(self, uri: str) -> str:
        """Gets the path of a file from a given URI.

        A URI is fully specified, including inforamation that
        is captured by the Storage (e.g. a storage account and container
        name or a base directory). This method will return the
        file path for the given URI.
        """
        pass

    def get_path_from_url(self, url: str) -> str:
        """Gets the path of a file from given HTTP URL."""
        return url.replace(self.get_url(""), "")

    @abstractmethod
    def get_substorage(self, path: str) -> "AsyncStorage":
        """Creates a new Storage that is scoped to the given path"""
        pass

    @abstractmethod
    async def read_bytes(self, file_path: str) -> bytes:
        """Reads bytes from a file in storage

        Args:
            file_path (str): Path to file.

        Returns:
            str: The contents of the file.
        """
        pass

    async def read_text(self, file_path: str) -> str:
        """Reads text from a file in storage

        Args:
            file_path (str): Path to file.

        Returns:
            str: The contents of the file.
        """
        return (await self.read_bytes(file_path)).decode("utf-8")

    async def read_json(self, file_path: str) -> Dict[str, Any]:
        """Reads a dict from a JSON file in storage.
        Args:
            file_path: Path to the JSON file.

        Returns:
            The Dict[str, Any] that is read from e.g. json.load
        """
        return orjson.loads(await self.read_bytes(file_path))

    @abstractmethod
    async def write_bytes(
        self, file_path: str, data: bytes, overwrite: bool = True
    ) -> None:
        """Writes bytes to a file.

        Args:
            file_path (str): Path to file.
            text: The text to write.
            overwrite: Overwrite if file is already present.
        """
        pass

    async def write_text(
        self, file_path: str, text: str, overwrite: bool = True
    ) -> None:
        """Writes a text file

        Args:
            file_path (str): Path to file.
            text: The text to write.
            overwrite: Overwrite if file is already present.
        """
        return await self.write_bytes(
            file_path, text.encode("utf-8"), overwrite=overwrite
        )

    async def write_dict(
        self, file_path: str, d: Dict[str, Any], overwrite: bool = True
    ) -> None:
        """Writes a text file

        Args:
            file_path (str): Path to file.
            text: The text to write.
            overwrite: Overwrite if file is already present.
        """
        return await self.write_bytes(file_path, orjson.dumps(d), overwrite=overwrite)

    @abstractmethod
    async def delete_folder(self, folder_path: str) -> None:
        """Deletes a folder (directory or blob prefix)

        Args:
            folder_path: The folder (e.g. a directory or blob prefix) to delete.
        """
        pass

    @abstractmethod
    async def delete_file(self, file_path: str) -> None:
        """Deletes a file

        Args:
            file_path: Path to the file to delete.
        """
        pass

    async def sign(self, href: str) -> str:
        """Appends a SAS Token to the HREFs.

        This is used by stactools to give proper read access
        to HREFs during processing.
        """
        path = self.get_path_from_url(href)
        return await self.get_authenticated_url(path)
