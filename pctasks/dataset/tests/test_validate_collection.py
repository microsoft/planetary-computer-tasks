import copy
import json
from tempfile import NamedTemporaryFile
from typing import Any, Dict

import pytest
from stac_validator import stac_validator

from pctasks.dataset import validate

collection: Dict[str, Any] = {
    "type": "Collection",
    "stac_version": "1.0.0",
    "id": "test",
    "title": "My datasets",
    "description": "My test datasets",
    "license": "CC-BY-4.0",
    "assets": {"thumbnail": {"href": "file.png"}, "other": {"href": "other.png"}},
    "msft:short_description": "short",
    "msft:storage_account": "account",
    "msft:container": "container",
    "providers": [
        {
            "name": "Microsoft",
            "roles": ["host"],
            "url": "https://planetarycomputer.microsoft.com/",
        }
    ],
    "links": [
        {
            "rel": "license",
            "href": "https://creativecommons.org/licenses/by/4.0/",
            "type": "text/html",
            "title": "My license",
        }
    ],
    "extent": {
        "spatial": {
            "bbox": [[-180.0, -81.33, 6.30, 81.33], [141.70, -81.33, 180.0, 81.33]]
        },
        "temporal": {"interval": [["2017-02-28T00:16:52Z", None]]},
    },
}


def test_validate_with_pystac() -> None:
    # Ensure our test collection is a valid collection
    with NamedTemporaryFile() as f:
        f.write(json.dumps(collection).encode("utf-8"))
        stac_validator.StacValidate(f.name)


def test_validate_ok() -> None:
    validate.validate_collection(collection)  # no errors!


def test_validate_required_keys() -> None:
    required_keys = [
        "msft:short_description",
        "msft:storage_account",
        "msft:container",
        "title",
    ]
    for key in required_keys:
        c = {k: v for k, v in collection.items() if k != key}

        with pytest.raises(ValueError, match=key):
            validate.validate_collection(c)


def test_validate_thumbnail() -> None:
    c = copy.deepcopy(collection)
    del c["assets"]["thumbnail"]  # type: ignore

    with pytest.raises(ValueError, match="thumbnail"):
        validate.validate_collection(c)

    del c["assets"]

    with pytest.raises(ValueError, match="thumbnail"):
        validate.validate_collection(c)


def test_validate_id_hyphens() -> None:
    c = copy.deepcopy(collection)
    c["id"] = "test_collection"
    with pytest.raises(
        ValueError, match="Collection id 'test_collection' should use hyphens"
    ):
        validate.validate_collection(c)


def test_microsoft_host():
    c = copy.deepcopy(collection)
    c["providers"][0]["name"] = "microsoft"
    with pytest.raises(ValueError, match="Provider 'Microsoft' should be titlecase"):
        validate.validate_collection(c)


def test_license_has_title():
    c = copy.deepcopy(collection)
    del c["links"][0]["title"]
    with pytest.raises(ValueError, match="license link must have a title"):
        validate.validate_collection(c)


def test_no_self_link():
    c = copy.deepcopy(collection)
    c["links"].append(
        {"rel": "self", "path": "home/template.json", "type": "application/json"}
    )
    with pytest.raises(ValueError, match="Collection should not have 'self' links"):
        validate.validate_collection(c)


def test_has_license_link() -> None:
    c = copy.deepcopy(collection)
    del c["links"][0]
    with pytest.raises(ValueError, match="must have license link"):
        validate.validate_collection(c)
