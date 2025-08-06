import json
import pathlib
from typing import List, Optional

import pystac
import pytest
import yaml

from pctasks.core.utils.template import (
    LocalTemplater,
    TemplateError,
    find_value,
    split_path,
    template_dict,
)

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


def test_template_new_types() -> None:
    params = {
        "force": True,
        "int_value": 1,
        "float_value": 1.0,
    }

    data = {
        "id": "something",
        "environment": {
            "force": r"${{ params.force }}",
            "int_value": r"${{ params.int_value }}",
            "float_value": r"${{ params.float_value }}",
        },
    }

    def _get_value(path: List[str]) -> Optional[str]:
        if path[0] == "params":
            return find_value(params, path[1:])

    result = template_dict(data, _get_value)

    assert result["id"] == "something"
    assert result["environment"]["force"]
    assert result["environment"]["int_value"] == 1
    assert result["environment"]["float_value"] == 1.0


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


def test_local_path_template_glob(tmp_path) -> None:
    p = tmp_path.joinpath("file-1.json")

    yaml_str = f"""
    key: ${{{{local.path({tmp_path}/*.json)}}}}
    """
    yaml_dict = yaml.safe_load(yaml_str)
    with pytest.raises(TemplateError, match="0"):
        templated_dict = LocalTemplater(base_dir=tmp_path).template_dict(yaml_dict)

    p.touch()
    templated_dict = LocalTemplater(base_dir=tmp_path).template_dict(yaml_dict)
    assert templated_dict["key"] == str(p)

    tmp_path.joinpath("file-2.json").touch()
    with pytest.raises(TemplateError, match="2"):
        templated_dict = LocalTemplater(base_dir=tmp_path).template_dict(yaml_dict)
