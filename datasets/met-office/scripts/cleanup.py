import json
import sys
from typing import Any

path = sys.argv[1]

dimensions = {}
variables = {}
with open(path) as f:
    data = json.load(f)


def update_dimensions(key: str, value: dict[str, Any]) -> None:
    if existing_dimension := dimensions.get(key):
        if existing_values := existing_dimension.get("values"):
            new_values = value["values"]
            if len(new_values) > len(existing_values):
                dimensions["values"] = new_values
    else:
        dimensions[key] = value


for item_asset in data["item_assets"].values():
    item_asset_dimensions = list()
    for key, value in item_asset["cube:dimensions"].items():
        update_dimensions(key, value)
        item_asset_dimensions.append(key)
    item_asset_dimensions += ["forecast:reference_datetime", "forecast:horizon"]
    for key, value in item_asset["cube:variables"].items():
        value["dimensions"] = item_asset_dimensions
        variables[key] = value

    del item_asset["cube:dimensions"]
    del item_asset["cube:variables"]

id = data["id"]
dimensions.update(
    {
        "forecast:reference_datetime": {
            "type": "temporal",
            "extent": ["2023-12-15T00:00:00Z", None],
        },
        "forecast:horizon": {
            "type": "temporal",
            "extent": [None, None],
            "values": [
                "PT0H",
                "PT1H",
                "PT2H",
                "PT3H",
                "PT4H",
                "PT5H",
                "PT6H",
                "PT7H",
                "PT8H",
                "PT9H",
                "PT10H",
                "PT11H",
                "PT12H",
                "PT13H",
                "PT14H",
                "PT15H",
                "PT16H",
                "PT17H",
                "PT18H",
                "PT19H",
                "PT20H",
                "PT21H",
                "PT22H",
                "PT23H",
                "PT24H",
                "PT25H",
                "PT26H",
                "PT27H",
                "PT28H",
                "PT29H",
                "PT30H",
                "PT31H",
                "PT32H",
                "PT33H",
                "PT34H",
                "PT35H",
                "PT36H",
                "PT37H",
                "PT38H",
                "PT39H",
                "PT40H",
                "PT41H",
                "PT42H",
                "PT43H",
                "PT44H",
                "PT45H",
                "PT46H",
                "PT47H",
                "PT48H",
                "PT49H",
                "PT50H",
                "PT51H",
                "PT52H",
                "PT53H",
                "PT54H",
                "PT57H",
                "PT60H",
                "PT63H",
                "PT66H",
                "PT69H",
                "PT72H",
                "PT75H",
                "PT78H",
                "PT81H",
                "PT84H",
                "PT87H",
                "PT90H",
                "PT93H",
                "PT96H",
                "PT99H",
                "PT102H",
                "PT105H",
                "PT108H",
                "PT111H",
                "PT114H",
                "PT117H",
                "PT120H",
                "PT123H",
                "PT126H",
                "PT129H",
                "PT132H",
                "PT135H",
                "PT138H",
                "PT141H",
                "PT144H",
                "PT150H",
                "PT156H",
                "PT162H",
                "PT168H",
            ]
            if "global" in id
            else [
                "PT0H",
                "PT1H",
                "PT2H",
                "PT3H",
                "PT4H",
                "PT5H",
                "PT6H",
                "PT7H",
                "PT8H",
                "PT9H",
                "PT10H",
                "PT11H",
                "PT12H",
                "PT13H",
                "PT14H",
                "PT15H",
                "PT16H",
                "PT17H",
                "PT18H",
                "PT19H",
                "PT20H",
                "PT21H",
                "PT22H",
                "PT23H",
                "PT24H",
                "PT25H",
                "PT26H",
                "PT27H",
                "PT28H",
                "PT29H",
                "PT30H",
                "PT31H",
                "PT32H",
                "PT33H",
                "PT34H",
                "PT35H",
                "PT36H",
                "PT37H",
                "PT38H",
                "PT39H",
                "PT40H",
                "PT41H",
                "PT42H",
                "PT43H",
                "PT44H",
                "PT45H",
                "PT46H",
                "PT47H",
                "PT48H",
                "PT49H",
                "PT50H",
                "PT51H",
                "PT52H",
                "PT53H",
                "PT54H",
                "PT57H",
                "PT60H",
                "PT63H",
                "PT66H",
                "PT69H",
                "PT72H",
                "PT75H",
                "PT78H",
                "PT81H",
                "PT84H",
                "PT87H",
                "PT90H",
                "PT93H",
                "PT96H",
                "PT99H",
                "PT102H",
                "PT105H",
                "PT108H",
                "PT111H",
                "PT114H",
                "PT117H",
                "PT120H",
            ],
        },
    }
)

data["description"] = "{{ collection.description }}"
data["assets"]["thumbnail"]["href"] = (
    f"https://ai4edatasetspublicassets.blob.core.windows.net/assets/pc_thumbnails/{id}.jpg"
)
data["assets"]["thumbnail"]["type"] = "image/jpeg"
data["msft:container"] = "staging"
data["msft:storage_account"] = "ukmoeuwest"
data["cube:dimensions"] = dimensions
data["cube:variables"] = variables

with open(path, "w") as f:
    json.dump(data, f, indent=2)
