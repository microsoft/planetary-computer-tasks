# this can be run with python -m pytest
# to ensure that the file is on sys.path
import pytest
import pathlib
import json
import azure.functions as func

import PublishItemsCF


HERE = pathlib.Path(__file__).parent

@pytest.fixture
def document() -> func.Document:
    data = json.load(pathlib.Path(HERE / "items_document.json").open())
    return func.Document(data)


def test_transform_document(document):
    result = PublishItemsCF.transform_document(document)
    assert result
