# this can be run with python -m pytest
# to ensure that the file is on sys.path
import json
import pathlib

import azure.functions as func
import PublishItemsCF
import pytest

HERE = pathlib.Path(__file__).parent


@pytest.fixture
def document() -> func.Document:
    data = json.load(pathlib.Path(HERE / "items_document.json").open())
    return func.Document(data["data"])


def test_transform_document(document):
    result = PublishItemsCF.transform_document(document)
    assert result
