import json
import pathlib
from typing import List, Optional

from pctasks.core.utils.template import find_value, split_path, template_dict
import pystac

HERE = pathlib.Path(__file__).parent
TEST_COLLECTION = HERE / "../data-files/planet-nicfi-analytic.json"


def test_template() -> None:
    params = {
        "l1-1": "a",
        "l1-2": {
            "l2-1": "b",
            "l2-2": ["one", "two"],
        },
    }

    data = {
        "id": "something",
        "environment": {
            "debug": True,
            "other": r"${{ params.l1-1 }}",
            "level2": r"${{ params.l1-2.l2-1 }}",
            "list": r"${{ params.l1-2.l2-2[1] }}",
        },
    }

    def _get_value(path: List[str]) -> Optional[str]:
        if path[0] == "params":
            return find_value(params, path[1:])

    result = template_dict(data, _get_value)

    assert result["id"] == "something"
    assert result["environment"]["other"] == "a"
    assert result["environment"]["level2"] == "b"
    assert result["environment"]["list"] == "two"


def test_split_path():
    s = "a.b.c"
    assert split_path(s) == ["a", "b", "c"]

    s = "a.func(b).c(test.json)"
    assert split_path(s) == ["a", "func(b)", "c(test.json)"]


def test_template_collection_passthrough() -> None:
    with open(TEST_COLLECTION) as f:
        collection_dict = json.load(f)

    collection = pystac.Collection.from_dict(collection_dict)

    collection.set_self_href("https://example.com/collections/test_collection")
    print(json.dumps(collection.to_dict(), indent=2))

    collection.validate()

    def _get_value(path: List[str]) -> Optional[str]:
        return None

    templated_collection_dict = template_dict(collection.to_dict(), _get_value)

    templated_collection = pystac.Collection.from_dict(templated_collection_dict)

    templated_collection.set_root(templated_collection)
    templated_collection.validate()
