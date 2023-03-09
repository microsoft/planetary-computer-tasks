import json
import pathlib

import pytest
from pypgstac.db import PgstacDB

from pctasks.core.storage import StorageFactory
from pctasks.dev.constants import AZURITE_ACCOUNT_KEY
from pctasks.dev.db import temp_pgstac_db
from pctasks.dev.queues import TempQueue
from pctasks.ingest.models import IngestCollectionsInput
from pctasks.ingest_task import streaming
from pctasks.ingest_task.task import IngestTask, IngestTaskInput
from pctasks.task.context import TaskContext
from pctasks.task.streaming import StreamingTaskOptions

HERE = pathlib.Path(__file__).parent


@pytest.fixture
def document():
    return json.loads((HERE / "items_document.json").read_text())


@pytest.fixture
def s1_grd_collection():
    return json.loads(
        (HERE / "../../../datasets/sentinel-1-grd/collection.json").read_text()
    )


@pytest.fixture
def conn_str_info(monkeypatch):
    monkeypatch.setenv("POSTGRES_USER", "username")
    monkeypatch.setenv("POSTGRES_PASSWORD", "password")
    monkeypatch.setenv("POSTGRES_DBNAME", "postgis")
    # monkeypatch.setenv("POSTGRES_USER", "username")
    monkeypatch.setenv("POSTGRES_PASS", "password")
    monkeypatch.setenv("POSTGRES_HOST", "localhost")
    monkeypatch.setenv("POSTGRES_PORT", "5499")
    monkeypatch.setenv(
        "DB_CONNECTION_STRING", "postgresql://username:password@localhost:5499/postgis"
    )
    # monkeypatch.setenv("PGDATABASE", "postgis")
    with temp_pgstac_db() as conn_str_info:
        yield conn_str_info


# TODO: currently failing. Need to ingest the collection
def test_streaming_create_items_task(conn_str_info, s1_grd_collection, document):
    # Relies on the servers running
    #   - azurite
    #   - pgstac
    context = TaskContext(run_id="test", storage_factory=StorageFactory())
    with PgstacDB(conn_str_info.local) as db:

        # ingest collection
        task = IngestTask()
        input = IngestTaskInput(
            content=IngestCollectionsInput(collections=[s1_grd_collection])
        )
        task.run(input, context)

        with TempQueue(
            message_decode_policy=None, message_encode_policy=None
        ) as queue_client:
            # put some messages on the queue
            for _ in range(10):
                queue_client.send_message(json.dumps(document))
            task_input = streaming.StreamingIngestItemsInput(
                collection_id="test",
                streaming_options=StreamingTaskOptions(
                    queue_url=queue_client.url,
                    queue_credential=AZURITE_ACCOUNT_KEY,
                    visibility_timeout=10,
                    message_limit=5,
                ),
            )

            # ingest items
            r = task = streaming.StreamingIngestItemsTask()
            task.run(task_input, context)

            results = list(
                db.query("select * from items where collection = 'sentinel-1-grd'")
            )
            assert len(results)
