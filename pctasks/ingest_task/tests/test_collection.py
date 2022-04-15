import json
import os
import pathlib
from typing import Any, Dict, cast

from pctasks.core.models.task import FailedTaskResult
from pctasks.dev.mocks import MockTaskContext
from pctasks.ingest.constants import DB_CONNECTION_STRING_ENV_VALUE
from pctasks.ingest.models import IngestTaskInput
from pctasks.ingest.utils import generate_collection_json
from pctasks.ingest_task.task import ingest_task
import pystac
from tests.conftest import ingest_test_environment

from pypgstac.db import PgstacDB

HERE = pathlib.Path(__file__).parent
TEST_COLLECTION = HERE / "data-files/test_collection.json"
TEST_COLLECTION_TEMPLATE_DIR = HERE / "data-files/era5-pds"


def test_collection():
    """Tests ingesting a collection into the dev db."""
    task_context = MockTaskContext.default()

    with ingest_test_environment():

        with open(TEST_COLLECTION, "r") as f:
            collection = json.load(f)
        print(json.dumps(collection, indent=2))

        result = ingest_task.run(
            input=IngestTaskInput(content=collection), context=task_context
        )

        assert not isinstance(result, FailedTaskResult)

        db = PgstacDB(dsn=os.environ[DB_CONNECTION_STRING_ENV_VALUE])
        row = db.query(
            f"SELECT content FROM collections WHERE id = '{collection['id']}'"
        )

        collection = pystac.Collection.from_dict(cast(Dict[str, Any], next(row)[0]))
        collection.set_self_href("https://example.com/collections/test_collection")
        collection.validate()


def test_collection_template():
    """Tests ingesting a collection template into the dev db."""
    task_context = MockTaskContext.default()

    with ingest_test_environment():

        collection = generate_collection_json(TEST_COLLECTION_TEMPLATE_DIR)

        input_model = IngestTaskInput(content=collection)
        input_model_yaml = input_model.to_yaml()
        print(input_model_yaml)
        input_model = IngestTaskInput.from_yaml(input_model_yaml)

        from pctasks.execute.models import TaskSubmitMessage
        from pctasks.core.models.task import TaskConfig
        from pctasks.core.models.dataset import DatasetIdentifier

        submit_msg = TaskSubmitMessage(
            instance_id="instance_id",
            dataset=DatasetIdentifier(name="test_dataset"),
            run_id="run_id",
            job_id="job",
            config=TaskConfig(
                id="task_id",
                image="mock-image",
                task="whatever.task",
                args=input_model.dict()
            )
        )

        print(submit_msg.json())
        raise Exception()

        result = ingest_task.run(
            input=input_model, context=task_context
        )

        assert not isinstance(result, FailedTaskResult)

        db = PgstacDB(dsn=os.environ[DB_CONNECTION_STRING_ENV_VALUE])
        row = db.query(
            f"SELECT content FROM collections WHERE id = '{collection['id']}'"
        )

        collection = pystac.Collection.from_dict(cast(Dict[str, Any], next(row)[0]))
        collection.set_self_href("https://example.com/collections/test_collection")
        collection.validate()
