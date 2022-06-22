from pathlib import Path
import textwrap
from pctasks.dev.blob import temp_azurite_blob_storage

from pctasks.dev.test_utils import (
    assert_workflow_is_successful,
    run_workflow,
)

HERE = Path(__file__).parent
COLLECTION_PATH = HERE / ".." / "data-files/modis/collection.json"
NDJSON_PATH = HERE / ".." / "data-files/modis/items.ndjson"

TIMEOUT_SECONDS = 60


def test_modis_ingest() -> None:
    collection_workflow = textwrap.dedent(
        """\
        name: Ingest Collection Test Workflow
        dataset: microsoft/modis-test



        jobs:
            ingest:
                name: Ingest Collection
                tasks:
                - id: ingest-collection
                  image: localhost:5001/pctasks-ingest:latest
                  task: pctasks.ingest_task.task:ingest_task
                  environment:
                    DB_CONNECTION_STRING: "${{ secrets.DB_CONNECTION_STRING }}"
                  args:
                    content:
                        type: Collections
                        collections:
                        - ${{ local.file(../data-files/collection.json) }}

        """
    )

    collection_run_id = run_workflow(
        collection_workflow,
        base_path=HERE,
    )

    assert_workflow_is_successful(collection_run_id, timeout_seconds=TIMEOUT_SECONDS)

    with temp_azurite_blob_storage(NDJSON_PATH) as storage:

        items_workflow = textwrap.dedent(
            """\
            name: Ingest Items Test Workflow
            dataset: microsoft/modis-test

            args:
            - ndjson_uri

            jobs:
                ingest:
                    name: Ingest Items
                    tasks:
                    - id: ingest-items
                      image: localhost:5001/pctasks-ingest:latest
                      task: pctasks.ingest_task.task:ingest_task
                      environment:
                        DB_CONNECTION_STRING: "${{ secrets.DB_CONNECTION_STRING }}"
                      args:
                        content:
                            type: Ndjson
                            uris:
                            - ${{ args.ndjson_uri }}


            """
        )

        items_run_id = run_workflow(
            items_workflow,
            args={"ndjson_uri": storage.get_uri("items.ndjson")},
        )

        assert_workflow_is_successful(items_run_id, timeout_seconds=TIMEOUT_SECONDS)
