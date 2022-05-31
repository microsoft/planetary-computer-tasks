from pathlib import Path

from pctasks.dev.test_utils import assert_workflow_is_successful, run_pctasks

HERE = Path(__file__).parent
COLLECTION_PATH = HERE / ".." / "data-files/modis/collection.json"
NDJSON_FOLDER_PATH = HERE / ".." / "data-files/modis"

TIMEOUT_SECONDS = 60


def test_modis_ingest() -> None:
    collection_ingest_result = run_pctasks(
        ["ingest", "collection", str(COLLECTION_PATH), "--submit"]
    )

    assert collection_ingest_result.exit_code == 0
    run_id = collection_ingest_result.output.strip()

    assert_workflow_is_successful(run_id, timeout_seconds=TIMEOUT_SECONDS)

    item_ingest_result = run_pctasks(
        [
            "ingest",
            "ndjsons",
            "modis-14A1-061",
            str(NDJSON_FOLDER_PATH),
            "--extension",
            ".ndjson",
            "--submit",
        ]
    )
    assert item_ingest_result.exit_code == 0
    print("ingest ndjsons output:", item_ingest_result.output)
    print(item_ingest_result.output)
    run_id = item_ingest_result.output.strip()

    assert_workflow_is_successful(run_id, timeout_seconds=TIMEOUT_SECONDS)
