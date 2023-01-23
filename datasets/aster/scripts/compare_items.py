#!/usr/bin/env python

from typing import Any, Dict, Set

from pystac_client import Client

LIMIT = 10

client = Client.open("https://pct-apis-staging.westeurope.cloudapp.azure.com/stac")
item_search = client.search(collections=["aster-l1t"], limit=LIMIT, max_items=LIMIT)
pc_test_items = item_search.item_collection()

client = Client.open("https://planetarycomputer.microsoft.com/api/stac/v1")
item_search = client.search(
    collections=["aster-l1t"], ids=[item.id for item in pc_test_items]
)
production_items = item_search.item_collection()


def compare_dicts(a: Dict[str, Any], b: Dict[str, Any]) -> None:
    keys_a = check_keys(a, b)
    keys_b = check_keys(b, a)
    keys = keys_a.intersection(keys_b)
    for key in keys:
        a_value = a[key]
        b_value = b[key]
        if type(a_value) != type(b_value):
            print(f"Types differ for key={key}: a={type(a_value)}, b={type(b_value)}")
        elif isinstance(a_value, dict):
            compare_dicts(a_value, b_value)
        elif isinstance(a_value, list):
            for i, (a_value, b_value) in enumerate(zip(a_value, b_value)):
                compare_values(a_value, b_value, f"{key}:{i}")
        else:
            compare_values(a_value, b_value, key)


def compare_values(a: Any, b: Any, key: str) -> None:
    if a != b:
        print(f"Values for key={key} are not equal: a={a}, b={b}")


def check_keys(a: Dict[str, Any], b: Dict[str, Any]) -> Set[str]:
    keys = set()
    for key in a.keys():
        if key in ("geometry", "bbox"):
            continue
        elif key not in b:
            print(f"key={key} in a but not in b")
        else:
            keys.add(key)
    return keys


for pc_test_item in pc_test_items:
    production_item = next(i for i in production_items if i.id == pc_test_item.id)
    print(f"Comparing {pc_test_item.id}")
    pc_test_item_as_dict = pc_test_item.to_dict(include_self_link=False)
    production_item_as_dict = production_item.to_dict(include_self_link=False)
    compare_dicts(pc_test_item_as_dict, production_item_as_dict)
    print()
