import logging
import multiprocessing
import os
import sys
from datetime import datetime as Datetime
from datetime import timedelta, timezone
from typing import (
    Any,
    Dict,
    Generator,
    Iterable,
    Iterator,
    List,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
)
from urllib.parse import urlparse

import azure.core.exceptions
from azure.identity import ClientSecretCredential as AzureClientSecretCredential
from azure.identity import DefaultAzureCredential
from azure.storage.blob import (
    BlobPrefix,
    BlobProperties,
    BlobServiceClient,
    ContainerClient,
    ContainerSasPermissions,
    ContentSettings,
    generate_container_sas,
)

from pctasks.core.constants import (
    AZURITE_HOST_ENV_VAR,
    AZURITE_PORT_ENV_VAR,
    AZURITE_STORAGE_ACCOUNT_ENV_VAR,
)
from pctasks.core.models.base import PCBaseModel
from pctasks.core.storage.base import Storage, StorageFileInfo
from pctasks.core.storage.path_filter import PathFilter
from pctasks.core.utils import map_opt
from pctasks.core.utils.backoff import with_backoff

logger = logging.getLogger(__name__)

T = TypeVar("T", bound="BlobStorage")


_AZURITE_ACCOUNT_KEY = (
    "Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6I"
    "FsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw=="
)


class ClientSecretCredentials(PCBaseModel):
    tenant_id: str
    client_id: str
    client_secret: str


class BlobStorageError(Exception):
    pass


class ResourceNoteFoundError(BlobStorageError):
    pass


class SasTokenError(Exception):
    pass


class BlobUri:
    """Represents a blob uri Azure Blob Storage.

    A blob URI can be to a specific blob, a prefix that represents
    many blobs, or only a storage account and container.

    The URIs are structured like this:
        ``blob://{storage_account_name}/{container_name}/{prefix}/blob.txt}``

    Attributes:
        * storage_account_name: The name of the storage account for this path.
        * container_name: The name of the container for this path
        * blob_name: the blob name or prefix, if exists. If not, None.
    """

    def __init__(self, uri: str) -> None:
        self.uri = uri
        parsed = urlparse(self.uri)
        self.storage_account_name: str = parsed.netloc
        self.container_name: str = parsed.path.split("/")[1]
        if not self.container_name:
            raise ValueError(
                f"BlobPath requires container name; {self.uri} is invalid."
            )
        self.blob_name: Optional[str] = "/".join(parsed.path.split("/")[2:]) or None

    def __repr__(self) -> str:
        return f"BlobUri({self.uri})"

    @property
    def url(self) -> str:
        """Gets the HTTPS URL for this blob path.

        Returns:
            str: The public URL of the blob.
        """
        result = (
            f"https://{self.storage_account_name}.blob.core.windows.net"
            f"/{self.container_name}"
        )
        if self.blob_name:
            result = f"{result}/{self.blob_name}"
        return result

    def __str__(self) -> str:
        result = f"blob://{self.storage_account_name}/{self.container_name}"
        if self.blob_name:
            result = f"{result}/{self.blob_name}"
        return result

    @property
    def base_uri(self) -> "BlobUri":
        """Returns the BlobUri for the storage account and container"""
        return BlobUri(f"blob://{self.storage_account_name}/{self.container_name}")

    @staticmethod
    def matches(uri: str) -> bool:
        """Checks to see if a uri is a blob uri"""
        try:
            parsed = urlparse(uri)
            return parsed.scheme == "blob"
        except Exception:
            return False


class ContainerClientWrapper:
    """Wrapper class that ensures closing of clients"""

    def __init__(
        self, account_client: BlobServiceClient, container_client: ContainerClient
    ) -> None:
        self._account_client = account_client
        self.container = container_client

    def __enter__(self) -> "ContainerClientWrapper":
        return self

    def __exit__(self, *args: Any) -> None:
        self.container.close()
        self._account_client.close()


class BlobStorage(Storage):
    """Utility class for blob storage access.
    Represents access to a single blob container, with an optional prefix.

    If a prefix is applied, then paths will be relative to that prefix.
    E.g. if BlobStorage for a BlobUri 'blob://somesa/some-container/some/folder'
    is used, then doing an operation like open_file on the file_path 'file.txt'
    will open the blob at 'blob://somesa/some-container/some/folder/file.txt'.

    Args:
        * storage_account_name: The storage account name,
            e.g. 'modissa'
        * container_name: The container name to access.
        * prefix: Optional prefix to base all paths off of.
        * sas_token: Optional  SAS token.
            If not supplied, uses DefaultAzureCredentials, in which you
            need to make sure the environment variables
            AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, and
            AZURE_TENANT_ID are set.
        * account_url: Optional account URL. If not supplied, uses
            the default Azure blob URL for a storage account.

    Note:

    If a service principle is used, make sure
    an appropriate IAM role (e.g. Storage Blob Data Contributor) on
    the storage account is assigned.

    See Storage for method docstrings.
    """

    _blob_creds: Union[
        AzureClientSecretCredential, DefaultAzureCredential, Dict[str, str], str
    ]

    def __init__(
        self,
        storage_account_name: str,
        container_name: str,
        prefix: Optional[str] = None,
        sas_token: Optional[str] = None,
        client_secret_credentials: Optional[ClientSecretCredentials] = None,
        account_url: Optional[str] = None,
    ) -> None:
        self.sas_token = sas_token

        # If this is the Azurite storage account, set
        # the account_url appropriately, and use
        # an account key. This is a workaround for
        # the SDK not handling Azurite well if it's not
        # at localhost or 127.0.0.1 (e.g. in a Docker container).
        is_azurite = False
        azurite_sa = os.getenv(AZURITE_STORAGE_ACCOUNT_ENV_VAR)

        if azurite_sa and azurite_sa == storage_account_name:
            host = os.getenv(AZURITE_HOST_ENV_VAR)
            port = os.getenv(AZURITE_PORT_ENV_VAR)
            if not host or not port:
                raise BlobStorageError(
                    "Azurite environment incorrectly configured. "
                    f"{AZURITE_HOST_ENV_VAR} and "
                    f"{AZURITE_PORT_ENV_VAR} must be set."
                )
            self.account_url = f"http://{host}:{port}/{azurite_sa}"
            self._blob_creds = {
                "account_name": storage_account_name,
                "account_key": _AZURITE_ACCOUNT_KEY,
            }
            is_azurite = True

        if not is_azurite:
            # Check if there's a service principle in the environment.
            # If so, use that. Otherwise check for a SAS token.
            if sas_token is not None:
                self._blob_creds = sas_token
            elif client_secret_credentials is not None:
                self._blob_creds = AzureClientSecretCredential(
                    client_id=client_secret_credentials.client_id,
                    client_secret=client_secret_credentials.client_secret,
                    tenant_id=client_secret_credentials.tenant_id,
                )
            elif os.environ.get("AZURE_CLIENT_ID"):
                self._blob_creds = DefaultAzureCredential()
            elif os.environ.get("AZURE_STORAGE_SAS_TOKEN"):
                self._blob_creds = os.environ["AZURE_STORAGE_SAS_TOKEN"]
            else:
                # Base case, let Azure SDK handle any other
                # possibility or error out.
                self._blob_creds = DefaultAzureCredential()

            self.account_url = (
                account_url or f"https://{storage_account_name}.blob.core.windows.net"
            )

        self.storage_account_name = storage_account_name
        self.container_name = container_name
        self.prefix = prefix.strip("/") if prefix is not None else prefix

    def __repr__(self) -> str:
        prefix_part = "" if self.prefix is None else f"/{self.prefix}"
        return (
            f"{self.__class__.__name__}(blob://{self.storage_account_name}"
            f"/{self.container_name}{prefix_part})"
        )

    def _get_client(self) -> ContainerClientWrapper:
        account_client = BlobServiceClient(
            account_url=self.account_url,
            credential=self._blob_creds,
        )

        container_client = account_client.get_container_client(self.container_name)

        return ContainerClientWrapper(account_client, container_client)

    def _get_name_starts_with(
        self, additional_prefix: Optional[str] = None
    ) -> Optional[str]:
        if self.prefix is not None:
            return os.path.join(self.prefix, additional_prefix or "")
        else:
            return additional_prefix

    def _add_prefix(self, path: str) -> str:
        if self.prefix is not None:
            return os.path.join(self.prefix, path)
        else:
            return path

    def _strip_prefix(self, path: str) -> str:
        if self.prefix is None:
            return path
        else:
            relpath = os.path.relpath(path.lstrip("/"), self.prefix)
            if relpath == ".":
                return ""
            return relpath

    @property
    def root_uri(self) -> str:
        container_uri = f"blob://{self.storage_account_name}/{self.container_name}"
        if self.prefix is None:
            return container_uri
        else:
            return os.path.join(container_uri, self.prefix)

    def get_substorage(self, path: str) -> "Storage":
        if self.prefix is None:
            subprefix = path
        else:
            subprefix = os.path.join(self.prefix, path)
        return BlobStorage(
            storage_account_name=self.storage_account_name,
            container_name=self.container_name,
            prefix=subprefix,
            sas_token=self.sas_token,
            account_url=self.account_url,
        )

    def get_url(self, file_path: str) -> str:
        return f"{self.account_url}/{self.container_name}/{self._add_prefix(file_path)}"

    def get_uri(self, file_path: Optional[str] = None) -> str:
        if file_path is None:
            return self.root_uri
        else:
            return os.path.join(self.root_uri, file_path)

    def _generate_container_sas(
        self,
        read: bool = True,
        list: bool = True,
        write: bool = False,
        delete: bool = False,
    ) -> str:
        """
        Generate a container-level SAS token.

        This uses the storage instance's BlobServiceClient (and its
        attached credentials) to generate a container-level SAS token.
        """
        start = Datetime.utcnow() - timedelta(hours=10)
        expiry = Datetime.utcnow() + timedelta(hours=24 * 7)
        permission = ContainerSasPermissions(
            read=read,
            write=write,
            delete=delete,
            list=list,
        )
        key = self._get_client()._account_client.get_user_delegation_key(
            key_start_time=start, key_expiry_time=expiry
        )
        sas_token = generate_container_sas(
            self.storage_account_name,
            self.container_name,
            user_delegation_key=key,
            permission=permission,
            start=start,
            expiry=expiry,
        )
        return sas_token

    def get_authenticated_url(
        self,
        file_path: str,
        read: bool = True,
        list: bool = True,
        write: bool = False,
        delete: bool = False,
    ) -> str:
        sas_token = self.sas_token
        if self.sas_token is None:
            sas_token = self._generate_container_sas(
                read=read, list=list, write=write, delete=delete
            )
        base_url = self.get_url(file_path)
        return f"{base_url}?{sas_token.lstrip('?')}"

    def get_path(self, uri: str) -> str:
        blob_uri = BlobUri(uri)
        if blob_uri.storage_account_name != self.storage_account_name:
            raise ValueError(f"URI {uri} does not share storage account with {self}")
        if blob_uri.container_name != self.container_name:
            raise ValueError(f"URI {uri} does not share container with {self}")
        if self.prefix:
            if not blob_uri.blob_name or self.prefix not in blob_uri.blob_name:
                raise ValueError(f"URI {uri} does not share prefix with {self}")
            return self._strip_prefix(blob_uri.blob_name)
        else:
            return blob_uri.blob_name or ""

    def get_file_info(self, file_path: str) -> StorageFileInfo:
        with self._get_client() as client:
            with client.container.get_blob_client(self._add_prefix(file_path)) as blob:
                try:
                    props = with_backoff(lambda: blob.get_blob_properties())
                except azure.core.exceptions.ResourceNotFoundError:
                    raise FileNotFoundError(f"File {file_path} not found in {self}")
                return StorageFileInfo(size=cast(int, props.size))

    def file_exists(self, file_path: str) -> bool:
        with self._get_client() as client:
            with client.container.get_blob_client(self._add_prefix(file_path)) as blob:
                return with_backoff(lambda: blob.exists())

    def list_files(
        self,
        name_starts_with: Optional[str] = None,
        since_date: Optional[Datetime] = None,
        extensions: Optional[List[str]] = None,
        ends_with: Optional[str] = None,
        matches: Optional[str] = None,
    ) -> Iterable[str]:
        # Ensure UTC set
        since_date = map_opt(lambda d: d.replace(tzinfo=timezone.utc), since_date)
        path_filter = PathFilter(
            extensions=extensions, ends_with=ends_with, matches=matches
        )

        def log_page(page: Iterator[BlobProperties]) -> Iterator[BlobProperties]:
            print(".", end="", flush=True, file=sys.stderr)
            return page

        def filter_page(page: Iterator[BlobProperties]) -> Iterator[BlobProperties]:
            def _f(b: BlobProperties) -> bool:
                if b.size == 0:
                    # ADLS Gen 2 creates empty files as directory placeholders.
                    return False
                if since_date:
                    if cast(Datetime, b.last_modified) >= since_date:
                        return False
                name: str = b.name  # type: ignore
                return path_filter(name)

            return filter(
                _f,
                page,
            )

        def transform_page(page: Iterator[BlobProperties]) -> Iterator[str]:
            return map(lambda b: self._strip_prefix(b["name"]), page)

        def fetch_blobs() -> Iterable[str]:
            pages = client.container.list_blobs(
                name_starts_with=self._get_name_starts_with(name_starts_with)
            ).by_page()
            filtered_pages = map(filter_page, pages)
            logged_pages = map(log_page, filtered_pages)
            transformed_page = map(transform_page, logged_pages)

            for page in transformed_page:
                for blob_name in page:
                    yield blob_name

        with self._get_client() as client:
            return with_backoff(fetch_blobs)

    def walk(
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
    ) -> Generator[Tuple[str, List[str], List[str]], None, None]:
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

        def _get_prefix_content(
            full_prefix: Optional[str],
        ) -> Tuple[List[str], List[str]]:
            folders = []
            files = []
            for item in client.container.walk_blobs(name_starts_with=full_prefix):
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
        with self._get_client() as client:
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

                    folders, files = _get_prefix_content(full_prefix)

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

    def download_file(
        self,
        file_path: str,
        output_path: str,
        is_binary: bool = True,
        timeout_seconds: Optional[int] = None,
        **kwargs: Any,
    ) -> None:
        if timeout_seconds is not None:
            kwargs["timeout"] = timeout_seconds

        with self._get_client() as client:
            with client.container.get_blob_client(self._add_prefix(file_path)) as blob:
                with open(output_path, "wb" if is_binary else "w") as f:
                    try:
                        # timeout raises an azure.core.exceptions.HttpResponseError: ("Connection broken: ConnectionResetError(104, 'Connection reset by peer')"  # noqa
                        with_backoff(lambda: blob.download_blob(**kwargs).readinto(f))
                    except azure.core.exceptions.ResourceNotFoundError:
                        raise FileNotFoundError(f"File {file_path} not found in {self}")

    def upload_bytes(
        self,
        data: bytes,
        target_path: str,
        overwrite: bool = True,
    ) -> None:
        with self._get_client() as client:
            with client.container.get_blob_client(
                self._add_prefix(target_path)
            ) as blob:

                def _upload() -> None:
                    blob.upload_blob(data, overwrite=overwrite)  # type: ignore

                with_backoff(_upload)

    def upload_file(
        self,
        input_path: str,
        target_path: str,
        overwrite: bool = True,
        content_type: Optional[str] = None,
    ) -> None:
        """
        Upload a file to blob storage.

        Parameters
        ----------
        content_type: str, optional
            The content type of the file. If provided, it will be set in
            the :class:`azure.storage.blob.ContentSettings` argument passed
            to :meth:`azure.storage.blob.BlobClient.upload_blob`.
        """
        kwargs = {}
        if content_type:
            kwargs["content_settings"] = ContentSettings(content_type=content_type)
        with self._get_client() as client:
            with client.container.get_blob_client(
                self._add_prefix(target_path)
            ) as blob:

                def _upload() -> None:
                    with open(input_path, "rb") as f:
                        blob.upload_blob(f, overwrite=overwrite, **kwargs)

                with_backoff(_upload)

    def read_bytes(self, file_path: str) -> bytes:
        try:
            blob_path = self._add_prefix(file_path)
            with self._get_client() as client:
                with client.container.get_blob_client(blob_path) as blob:
                    blob_data = with_backoff(
                        lambda: blob.download_blob(
                            max_concurrency=multiprocessing.cpu_count() or 1
                        )
                    )
                    return cast(
                        bytes,
                        blob_data.readall(),
                    )
        except azure.core.exceptions.ResourceNotFoundError as e:
            raise FileNotFoundError(f"File {file_path} not found in {self}") from e
        except Exception as e:
            raise BlobStorageError(
                f"Could not read text from {self.get_uri(file_path)}"
            ) from e

    def write_bytes(self, file_path: str, data: bytes, overwrite: bool = True) -> None:
        full_path = self._add_prefix(file_path)
        with self._get_client() as client:
            with client.container.get_blob_client(full_path) as blob:
                with_backoff(
                    lambda: blob.upload_blob(data, overwrite=overwrite)  # type: ignore
                )

    def delete_folder(self, folder_path: Optional[str] = None) -> None:
        for file_path in self.list_files(name_starts_with=folder_path):
            self.delete_file(file_path)

    def delete_file(self, file_path: str) -> None:
        with self._get_client() as client:
            with client.container.get_blob_client(self._add_prefix(file_path)) as blob:
                try:
                    with_backoff(lambda: blob.delete_blob())
                except azure.core.exceptions.ResourceNotFoundError:
                    raise FileNotFoundError(f"File {file_path} not found in {self}")

    @classmethod
    def from_uri(
        cls: Type[T],
        blob_uri: Union[BlobUri, str],
        sas_token: Optional[str] = None,
        client_secret_credentials: Optional[ClientSecretCredentials] = None,
        account_url: Optional[str] = None,
    ) -> T:
        if isinstance(blob_uri, str):
            blob_uri = BlobUri(blob_uri)

        return cls(
            storage_account_name=blob_uri.storage_account_name,
            container_name=blob_uri.container_name,
            prefix=blob_uri.blob_name,
            sas_token=sas_token,
            client_secret_credentials=client_secret_credentials,
            account_url=account_url,
        )

    @classmethod
    def from_account_key(
        cls: Type[T],
        blob_uri: Union[BlobUri, str],
        account_key: str,
        account_url: Optional[str] = None,
    ) -> T:
        if isinstance(blob_uri, str):
            blob_uri = BlobUri(blob_uri)

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

    @property
    def fsspec_storage_options(self) -> Dict[str, str]:
        return {"account_name": self.storage_account_name}

    def fsspec_path(self, path: str) -> str:
        """
        Return the fsspec-style path.
        """
        return f"abfs://{self.container_name}/{path}"

    @classmethod
    def from_connection_string(
        cls: Type[T],
        connection_string: str,
        container_name: str,
    ) -> T:
        container_client = ContainerClient.from_connection_string(
            connection_string, container_name
        )
        credential = container_client.credential
        return cls.from_account_key(
            f"blob://{credential.account_name}/{container_name}", credential.account_key
        )


def maybe_rewrite_blob_storage_url(url: str) -> str:
    """
    Rewrite HTTP blob-storage URLs to blob:// URLs.

    If `url` isn't a blob-storage style URL, it's returned unmodified.

    Parameters
    ----------
    url: str
        The URL (or path) to a file.

    Returns
    -------
    str
        The rewritten URL. Blob Storage URLs are modified to use the `blob://`
        style. Non-blob storage URLs are returned unmodified.

    Examples
    --------
    Blob storage URLs are rewritten

    >>> maybe_rewrite_blob_storage_url(
    ...     "https://example.blob.core.windows.net/container/path/file.txt"
    ... )
    'blob://example/container/path/file.txt'

    Azurite-style URLs *are* rewritten

    >>> maybe_rewrite_blob_storage_url(
    ...     "https://azurite:10000/devstoreaccount1/container/path/file.txt"
    ... )
    'blob://azurite:10000/devstoreaccount1/container/path/file.txt'

    >>> maybe_rewrite_blob_storage_url(
    ...     "https://localhost:10000/devstoreaccount1/container/path/file.txt"
    ... )
    'blob://localhost:10000/devstoreaccount1/container/path/file.txt'

    Local paths are not affected

    >>> maybe_rewrite_blob_storage_url("path/file.txt")
    'path/file.txt'
    """
    parsed = urlparse(url)

    if parsed.netloc.endswith(".blob.core.windows.net"):
        account = parsed.netloc.split(".", 1)[0].strip("/")
        # TODO: this could maybe fail if the path is just to the container.
        container, path = parsed.path.strip("/").split("/", 1)

        url = f"blob://{account}/{container}/{path}"

    elif parsed.netloc.startswith(("azurite", "localhost", "127.0.0.1")):
        # should we *just* do port 10000?
        # Look at BlobStorage.__init__ maybe
        url = f"blob://{parsed.path.strip('/')}"

    return url
