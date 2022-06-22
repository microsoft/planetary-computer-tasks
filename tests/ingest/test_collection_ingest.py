from pathlib import Path

from pctasks.dev.test_utils import assert_workflow_is_successful, run_workflow_from_file

HERE = Path(__file__).parent
WORKFLOWS = HERE / ".." / "workflows"

TIMEOUT_SECONDS = 60


def test_ingest_collection():
    run_id = run_workflow_from_file(WORKFLOWS / "ingest-collection.yaml")
    assert_workflow_is_successful(run_id, timeout_seconds=TIMEOUT_SECONDS)
