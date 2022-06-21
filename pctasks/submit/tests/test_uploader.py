import os
import pathlib
import tempfile
from pctasks.dev.blob import temp_azurite_blob_storage
from pctasks.submit.code_uploader import upload_code
from pctasks.submit.settings import SubmitSettings
from pctasks.dev.constants import (
    AZURITE_ACCOUNT_KEY,
    AZURITE_ACCOUNT_NAME,
    AZURITE_HOST_ENV_VAR,
    TEST_DATA_CONTAINER,
)


def test_upload_code():
    hostname = os.getenv(AZURITE_HOST_ENV_VAR, "localhost")
    account_url = f"http://{hostname}:10000/devstoreaccount1"

    submit_settings = SubmitSettings(account_url=account_url, account_key=AZURITE_ACCOUNT_KEY, queue_name="queue")
    with tempfile.TemporaryDirectory() as td:
        p = pathlib.Path(td) / "myfile.py"
        p.write_text("test")
        with temp_azurite_blob_storage() as storage:
            result = upload_code(p, submit_settings)

    assert result == "blob://devstoreaccount1/code/098f6bcd4621d373cade4e832627b4f6/myfile.py"