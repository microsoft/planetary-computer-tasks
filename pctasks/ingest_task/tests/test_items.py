import json
import pathlib

from pctasks.core.models.task import FailedTaskResult
from pctasks.dev.mocks import MockTaskContext
from pctasks.ingest.models import (
    IngestNdjsonInput,
    IngestTaskConfig,
    IngestTaskInput,
    NdjsonFolder,
)
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


def test_ingest_ndjson_add_service_principal():
    result = IngestTaskConfig.from_ndjson(
        ndjson_data=IngestNdjsonInput(ndjson_folder=NdjsonFolder(uri="test/")),
        add_service_principal=True,
    )

    assert result.environment["AZURE_TENANT_ID"] == "${{ secrets.task-tenant-id }}"
    assert result.environment["AZURE_CLIENT_ID"] == "${{ secrets.task-client-id }}"
    assert (
        result.environment["AZURE_CLIENT_SECRET"] == "${{ secrets.task-client-secret }}"
    )

    result = IngestTaskConfig.from_ndjson(
        ndjson_data=IngestNdjsonInput(ndjson_folder=NdjsonFolder(uri="test/")),
        environment={"AZURE_TENANT_ID": "test"},
        add_service_principal=True,
    )
    assert result.environment["AZURE_TENANT_ID"] == "test"
    assert result.environment["AZURE_CLIENT_ID"] == "${{ secrets.task-client-id }}"
    assert (
        result.environment["AZURE_CLIENT_SECRET"] == "${{ secrets.task-client-secret }}"
    )

    result = IngestTaskConfig.from_ndjson(
        ndjson_data=IngestNdjsonInput(ndjson_folder=NdjsonFolder(uri="test/")),
    )
    assert "AZURE_TENANT_ID" not in result.environment
    assert "AZURE_TENANT_ID" not in result.environment
    assert "AZURE_TENANT_ID" not in result.environment
