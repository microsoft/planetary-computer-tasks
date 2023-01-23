import json
from pathlib import Path

from pctasks.dev.db import temp_pgstac_db
from pctasks.dev.test_utils import assert_workflow_is_successful, run_workflow_from_file
from tests.constants import DEFAULT_TIMEOUT

HERE = Path(__file__).parent
WORKFLOWS = HERE / ".." / "workflows"

TIMEOUT_SECONDS = DEFAULT_TIMEOUT


def test_ingest_collection():
    with temp_pgstac_db() as conn_str_info:
        collection_path = HERE / ".." / "data-files" / "collection.json"
        with collection_path.open() as f:
            collection = json.load(f)
        run_id = run_workflow_from_file(
            WORKFLOWS / "ingest-collection.yaml",
            args={"collection": collection, "db_connection_str": conn_str_info.remote},
        )
        assert_workflow_is_successful(run_id, timeout_seconds=TIMEOUT_SECONDS)
