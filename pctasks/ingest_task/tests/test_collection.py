import json
import os
import pathlib
from typing import Any, Dict, cast

import pystac
from pypgstac.db import PgstacDB

from pctasks.core.models.task import FailedTaskResult
from pctasks.dev.mocks import MockTaskContext
from pctasks.ingest.constants import DB_CONNECTION_STRING_ENV_VAR
from pctasks.ingest.models import IngestTaskInput
from pctasks.ingest.utils import generate_collection_json
from pctasks.ingest_task.task import ingest_task
from tests.conftest import ingest_test_environment

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

        db = PgstacDB(dsn=os.environ[DB_CONNECTION_STRING_ENV_VAR])
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
        input_model = IngestTaskInput.from_yaml(input_model_yaml)

        result = ingest_task.run(input=input_model, context=task_context)

        assert not isinstance(result, FailedTaskResult)

        db = PgstacDB(dsn=os.environ[DB_CONNECTION_STRING_ENV_VAR])
        row = db.query(
            f"SELECT content FROM collections WHERE id = '{collection['id']}'"
        )

        collection = pystac.Collection.from_dict(cast(Dict[str, Any], next(row)[0]))
        collection.set_self_href("https://example.com/collections/test_collection")
        collection.validate()
