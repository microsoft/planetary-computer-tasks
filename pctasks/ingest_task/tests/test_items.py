import json
import pathlib

from pctasks.core.models.task import FailedTaskResult
from pctasks.dev.mocks import MockTaskContext
from pctasks.ingest.models import IngestNdjsonInput, IngestTaskInput
from pctasks.ingest_task.task import ingest_task
from tests.conftest import ingest_test_environment

HERE = pathlib.Path(__file__).parent
TEST_COLLECTION = HERE / "data-files/test_collection.json"
TEST_SINGLE_ITEM = HERE / "data-files/items/item1.json"
TEST_NDJSON = HERE / "data-files/items/items.ndjson"


def test_single_item_ingest():
    """Test ingesting Items through the ingest task logic."""

    task_context = MockTaskContext.default()

    with ingest_test_environment():

        # Ensure collection is ingested
        with open(TEST_COLLECTION, "r") as f:
            ingest_task.run(
                input=IngestTaskInput(content=json.load(f)),
                context=task_context,
            )

        # Ingest an item
        with open(TEST_SINGLE_ITEM, "r") as f:
            item = json.load(f)

        print(json.dumps(IngestTaskInput(content=item).dict(), indent=2))
        result = ingest_task.run(
            input=IngestTaskInput(content=item), context=task_context
        )

        assert not isinstance(result, FailedTaskResult)


def test_ndjson_ingest():
    """Test ingesting Items through the ingest task logic."""

    task_context = MockTaskContext.default()

    with ingest_test_environment():

        # Ensure collection is ingested
        with open(TEST_COLLECTION, "r") as f:
            ingest_task.run(
                input=IngestTaskInput(content=json.load(f)),
                context=task_context,
            )

        # Ingest Ndjson
        message_data = IngestTaskInput(
            content=IngestNdjsonInput(uris=[str(TEST_NDJSON.absolute())])
        )

        result = ingest_task.run(input=message_data, context=task_context)

        assert not isinstance(result, FailedTaskResult)
