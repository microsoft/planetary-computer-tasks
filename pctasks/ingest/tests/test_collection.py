import json
import pathlib
from typing import Any, Dict

import pystac

from pctasks.core.models.workflow import WorkflowDefinition
from pctasks.ingest.models import IngestTaskConfig, IngestTaskInput

HERE = pathlib.Path(__file__).parent
TEST_COLLECTION = HERE / "data-files/test_collection.json"
TEST_GOES_WORKFLOW = HERE / "data-files/goes-collection-workflow.yaml"


def test_collection_ser() -> None:
    with open(TEST_COLLECTION, "r") as f:
        collection = json.load(f)

    task = IngestTaskConfig.from_collection(collection=collection, target="staging")

    input = IngestTaskInput.parse_obj(task.args)
    ser_collection = input.content
    assert collection == ser_collection


def test_goes_coll_deser() -> None:
    with open(TEST_GOES_WORKFLOW, "r") as f:
        workflow = WorkflowDefinition.from_yaml(f.read())

    task = workflow.jobs["ingest-collection"].tasks[0]
    input = IngestTaskInput.parse_obj(task.args)
    assert isinstance(input.content, dict)
    collection_dict: Dict[str, Any] = input.content
    collection = pystac.Collection.from_dict(collection_dict)
    collection.set_self_href("https://example.com/collection.json")
    collection.validate()
