import json
import pathlib

from pctasks.core.models.task import FailedTaskResult
from pctasks.dev.mocks import MockTaskContext
from pctasks.ingest.models import IngestTaskInput
from pctasks.ingest_task.task import ingest_task
from tests.conftest import ingest_test_environment

HERE = pathlib.Path(__file__).parent
TEST_COLLECTION = HERE / "data-files/test_collection.json"


def test_collection():
    """Tests ingesting a collection into the dev db."""
    task_context = MockTaskContext.default()

    with ingest_test_environment():

        with open(TEST_COLLECTION, "r") as f:
            collection = json.load(f)

            result = ingest_task.run(
                input=IngestTaskInput(content=collection), context=task_context
            )

        assert not isinstance(result, FailedTaskResult)
