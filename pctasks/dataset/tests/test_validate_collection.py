import copy
import json
from tempfile import NamedTemporaryFile
from typing import Any, Dict

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
    "msft:region": "westeurope",
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
    _, errors = validate.validate_collection(collection)  # no errors!
    assert errors == []


def test_validate_required_keys() -> None:
    required_keys = [
        "msft:short_description",
        "msft:storage_account",
        "msft:container",
        "msft:region",
        "title",
    ]
    for key in required_keys:
        c = {k: v for k, v in collection.items() if k != key}
        _, errors = validate.validate_collection(c)

        for error in errors:
            assert key in error


def test_validate_thumbnail() -> None:
    c = copy.deepcopy(collection)
    del c["assets"]["thumbnail"]  # type: ignore

    _, (error,) = validate.validate_collection(c)
    assert "thumbnail" in error

    del c["assets"]
    _, (error,) = validate.validate_collection(c)
    assert "thumbnail" in error


def test_validate_id_hyphens() -> None:
    c = copy.deepcopy(collection)
    c["id"] = "test_collection"
    _, [error] = validate.validate_collection(c)
    assert (
        error == "Collection id 'test_collection' should use hyphens, not underscores."
    )


def test_microsoft_host():
    c = copy.deepcopy(collection)
    c["providers"][0]["name"] = "microsoft"

    _, [error] = validate.validate_collection(c)
    assert error == "Provider 'Microsoft' should be titlecase. Got microsoft instead."


def test_license_has_title():
    c = copy.deepcopy(collection)
    del c["links"][0]["title"]
    _, [error] = validate.validate_collection(c)
    assert error == "license link must have a title."


# def test_no_self_link():
#     c = copy.deepcopy(collection)
#     c["links"].append(
#         {"rel": "self", "path": "home/template.json", "type": "application/json"}
#     )
#     _, [error] = validate.validate_collection(c)
#     assert error == "Collection should not have 'self' links."


def test_has_license_link() -> None:
    c = copy.deepcopy(collection)
    del c["links"][0]

    _, [error] = validate.validate_collection(c)
    assert error == "must have license link"


def test_msft_region_format() -> None:
    c = copy.deepcopy(collection)
    c["msft:region"] = "West Europe"
    _, [error] = validate.validate_collection(c)
    assert error == "'msft:region' should not contain any spaces."