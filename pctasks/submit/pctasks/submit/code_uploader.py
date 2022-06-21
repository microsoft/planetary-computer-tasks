import os
import io
import hashlib
import pathlib
import urllib.parse
import zipfile

from pctasks.submit.settings import SubmitSettings
from pctasks.core.storage.blob import BlobStorage


def upload_code(path: os.PathLike, settings: SubmitSettings) -> str:
    """
    Uploads the code at ``path`` to the location determined by ``settings``.
    """
    # for now we assume the submitter is able to access blob storage directly.
    # TODO: Handle (some) remote URLs
    # TODO: Include some kind of unique run ID or content hashing.

    path = pathlib.Path(path)

    if not path.exists():
        raise OSError(f"Path {path} does not exist.")

    if path.is_file():
        data = path.read_bytes()
        name = path.name
    else:
        buf = io.BytesIO()
        with zipfile.PyZipFile(buf, "w") as zf:
            zf.writepy(str(path))

        data = buf.getvalue()
        name = path.with_suffix(".zip").name

    # TODO: Hash the data and include it in the name.

    parsed = urllib.parse.urlparse(settings.account_url)
    storage_account_name = parsed.netloc.split(".")[0]
    if storage_account_name in {"localhost:10000", "azurite:10000"}:
        # why this special case?
        storage_account_name = "devstoreaccount1"

    token = hashlib.md5(data).hexdigest()

    blob_uri = f"blob://{storage_account_name}/code/{token}"

    storage = BlobStorage.from_account_key(
        account_key=settings.account_key,
        account_url=settings.account_url,
        blob_uri=blob_uri,
    )
    storage.upload_bytes(data, name)
    return os.path.join(blob_uri, name)