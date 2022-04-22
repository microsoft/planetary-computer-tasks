import os
import sys
import multiprocessing
from typing import Any, Optional, AsyncIterable, AsyncIterator, Iterator, AsyncGenerator, Tuple, List, cast, Union
from datetime import datetime as Datetime
from datetime import timedelta, timezone

from azure.storage.blob import BlobProperties
from azure.storage.blob.aio import BlobServiceClient, ContainerClient
from azure.storage.blob.aio._list_blobs_helper import BlobPrefix  # TODO: use a public API

from pctasks.core.storage.base import StorageFileInfo
from pctasks.core.storage.async_base import AsyncStorage
from pctasks.core.storage.blob import BlobStorageMixin, BlobStorageError, BlobUri, generate_container_sas, ContainerSasPermissions
from pctasks.core.utils import map_opt
from pctasks.core.utils.backoff import async_with_backoff
from pctasks.core.storage.path_filter import PathFilter


class ContainerClientWrapper:
    """Wrapper class that ensures closing of clients"""

    def __init__(
        self, account_client: BlobServiceClient, container_client: ContainerClient
    ) -> None:
        self._account_client = account_client
        self.container = container_client

    async def __aenter__(self) -> "ContainerClientWrapper":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.container.close()
        await self._account_client.close()



class AsyncBlobStorage(BlobStorageMixin, AsyncStorage):
    # TODO: deduplicate. Put a ContainerClientWrapper type on cls
    def _get_client(self) -> ContainerClientWrapper:
        account_client = BlobServiceClient(
            account_url=self.account_url,
            credential=self._blob_creds,
        )

        container_client = account_client.get_container_client(self.container_name)

        return ContainerClientWrapper(account_client, container_client)

    async def list_files(self, name_starts_with: Optional[str] = None, since_date: Optional[Datetime] = None, extensions: Optional[List[str]] = None, ends_with: Optional[str] = None, matches: Optional[str] = None) -> AsyncIterable[str]:
       # Ensure UTC set
        since_date = map_opt(lambda d: d.replace(tzinfo=timezone.utc), since_date)
        path_filter = PathFilter(
            extensions=extensions, ends_with=ends_with, matches=matches
        )

        # async def fetch_blobs() -> AsyncIterable[str]:
        async with self._get_client() as client:
            pages = client.container.list_blobs(
                name_starts_with=self._get_name_starts_with(name_starts_with)
            ).by_page()

            async for page in pages:
                print(".", end="", flush=True, file=sys.stderr)
                async for blob in page:
                    # filter_page
                    if blob.size == 0:
                        continue
                    if since_date and blob.last_modified >= since_date:
                        # TODO: does this seem backwards?
                        continue
                    # log_page
                    filtered = path_filter(blob.name)
                    if filtered:
                        transformed = self._strip_prefix(blob["name"])
                        yield transformed

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
        # Ensure UTC set
        since_date = map_opt(lambda d: d.replace(tzinfo=timezone.utc), since_date)

        if name_starts_with and not name_starts_with.endswith("/"):
            name_starts_with = name_starts_with + "/"

        def _get_depth(path: Optional[str]) -> int:
            if not path:
                return 0
            path = path.strip("/")
            if self.prefix is not None:
                relpath = os.path.relpath(path, self.prefix)
                if relpath == ".":
                    return 0
            else:
                relpath = path
            if not relpath:
                return 0
            return len(relpath.split("/"))

        async def _get_prefix_content(
            full_prefix: Optional[str],
        ) -> Tuple[List[str], List[str]]:
            folders = []
            files = []
            # What is going on with this walk blobs? It doesn't look like the sync version
            async for item in client.container.walk_blobs(name_starts_with=full_prefix):
                item_name: str = cast(str, item.name)
                name = os.path.relpath(item_name, full_prefix)
                if isinstance(item, BlobPrefix):
                    folders.append(name.strip("/"))
                else:
                    if item.size == 0:
                        # ADLS Gen 2 creates empty files as directory placeholders.
                        continue
                    if since_date:
                        if cast(Datetime, item.last_modified) < since_date:
                            continue
                    files.append(name)
            return folders, files

        path_filter = PathFilter(
            extensions=extensions, ends_with=ends_with, matches=matches
        )

        walk_count = 0
        file_count = 0
        limit_break = False

        full_prefixes: List[str] = [self._get_name_starts_with(name_starts_with) or ""]
        async with self._get_client() as client:
            while full_prefixes:
                if walk_limit and walk_count >= walk_limit:
                    break

                if limit_break:
                    break

                next_level_prefixes: List[str] = []
                for full_prefix in full_prefixes:
                    if walk_limit and walk_count >= walk_limit:
                        limit_break = True
                        break
                    if limit_break:
                        break

                    prefix_depth = _get_depth(full_prefix)
                    if max_depth and prefix_depth > max_depth:
                        break

                    folders, files = await _get_prefix_content(full_prefix)

                    files = [file for file in files if path_filter(file)]

                    if file_limit and file_count + len(files) > file_limit:
                        files = files[: file_limit - file_count]
                        limit_break = True
                        if not files:
                            break

                    root = self._strip_prefix(full_prefix or "") or "."
                    walk_count += 1

                    next_level_prefixes.extend(
                        map(
                            lambda f: f"{os.path.join(full_prefix, f)}/",
                            folders,
                        )
                    )
                    file_count += len(files)
                    if not min_depth or prefix_depth >= min_depth:
                        yield root, folders, files

                full_prefixes = next_level_prefixes

    async def download_file(
        self,
        file_path: str,
        output_path: str,
        is_binary: bool = True,
    ) -> None:
        async with self._get_client() as client:
            async with client.container.get_blob_client(self._add_prefix(file_path)) as blob:
                with open(output_path, "wb" if is_binary else "w") as f:
                    async def fn():
                        stream = await blob.download_blob()
                        await stream.readinto(f)
                        
                    await async_with_backoff(fn)

    async def file_exists(self, file_path: str) -> bool:
        with self._get_client() as client:
            with client.container.get_blob_client(self._add_prefix(file_path)) as blob:
                async def fn():
                    return await blob.exists()
                return await async_with_backoff(fn)

    async def get_file_info(self, file_path: str) -> StorageFileInfo:
        with self._get_client() as client:
            with client.container.get_blob_client(file_path) as blob:
                async def fn():
                    return await blob.get_blob_properties()
                props = await async_with_backoff(fn)
                return StorageFileInfo(size=cast(int, props.size))

    async def upload_file(
        self,
        input_path: str,
        target_path: str,
        overwrite: bool = True,
    ) -> None:
        async with self._get_client() as client:
            async with client.container.get_blob_client(
                self._add_prefix(target_path)
            ) as blob:

                async def _upload() -> None:
                    with open(input_path, "rb") as f:
                        await blob.upload_blob(f, overwrite=overwrite)

                await async_with_backoff(_upload)

    def get_substorage(self, path: str) -> "Storage":
        if self.prefix is None:
            subprefix = path
        else:
            subprefix = os.path.join(self.prefix, path)
        return type(self)(
            storage_account_name=self.storage_account_name,
            container_name=self.container_name,
            prefix=subprefix,
            sas_token=self.sas_token,
            account_url=self.account_url,
        )

    async def read_bytes(self, file_path: str) -> bytes:
        try:
            blob_path = self._add_prefix(file_path)
            with self._get_client() as client:
                with client.container.get_blob_client(blob_path) as blob:
                    async def fn():
                        stream = await blob.download_blob(max_concurrency=multiprocessing.cpu_count() or 1)
                        return await stream.readall()

                    blob_data = await async_with_backoff(fn)

                    return cast(
                        bytes,
                        blob_data
                    )
        except Exception as e:
            raise BlobStorageError(
                f"Could not read text from {self.get_uri(file_path)}"
            ) from e

    async def delete_folder(self, folder_path: Optional[str] = None) -> None:
        async for file_path in self.list_files(name_starts_with=folder_path):
            await self.delete_file(file_path)

    async def delete_file(self, file_path: str) -> None:
        async with self._get_client() as client:
            with client.container.get_blob_client(self._add_prefix(file_path)) as blob:
                await blob.delete_blob()

    async def write_bytes(self, file_path: str, data: bytes, overwrite: bool = True) -> None:
        full_path = self._add_prefix(file_path)
        async with self._get_client() as client:
            async with client.container.get_blob_client(full_path) as blob:
                async def fn():
                    await blob.upload_blob(data, overwrite=overwrite)
                await async_with_backoff(fn)

    def __repr__(self) -> str:
        prefix_part = "" if self.prefix is None else f"/{self.prefix}"
        return (
            f"BlobStorage(blob://{self.storage_account_name}"
            f"/{self.container_name}{prefix_part})"
        )

    @classmethod
    def from_account_key(
        cls,
        blob_uri: Union[BlobUri, str],
        account_key: str,
        account_url: Optional[str] = None,
    ) -> "AsyncBlobStorage":
        if isinstance(blob_uri, str):
            blob_uri = BlobUri(blob_uri)

        # XXX: Figure out if this blocks
        sas_token = generate_container_sas(
            account_name=blob_uri.storage_account_name,
            container_name=blob_uri.container_name,
            account_key=account_key,
            start=Datetime.utcnow() - timedelta(hours=10),
            expiry=Datetime.utcnow() + timedelta(hours=24 * 7),
            permission=ContainerSasPermissions(
                read=True,
                write=True,
                delete=True,
                list=True,
            ),
        )

        return cls.from_uri(
            blob_uri=blob_uri, sas_token=sas_token, account_url=account_url
        )


