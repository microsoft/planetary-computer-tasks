import json

import deepdiff
import pystac_client

TEST_ENDPOINT = "https://pct-apis-staging.westeurope.cloudapp.azure.com/stac"
PROD_ENDPOINT = "https://planetarycomputer.microsoft.com/api/stac/v1"

COLLECTIONS = [
    "09A1",
    "09Q1",
    "10A1",
    "10A2",
    "11A1",
    "11A2",
    "13A1",
    "13Q1",
    "14A1",
    "14A2",
    "15A2H",
    "15A3H",
    "16A3GF",
    "17A2H",
    "17A2HGF",
    "17A3HGF",
    "21A2",
    "43A4",
    "64A1",
]

for collection in COLLECTIONS:
    test_client = pystac_client.Client.open(TEST_ENDPOINT)
    test_coll = test_client.get_collection(f"modis-{collection}-061")
    test_item = next(test_coll.get_items())

    prod_client = pystac_client.Client.open(PROD_ENDPOINT)
    prod_coll = prod_client.get_collection(f"modis-{collection}-061")
    prod_item = prod_coll.get_item(test_item.id)

    diff = deepdiff.DeepDiff(test_item.to_dict() , prod_item.to_dict() , ignore_order=True)
    # print(json.dumps(json.loads(diff.to_json()), indent=4))

    # filter out hrefs, etc, save to json file


