#!/usr/bin/env python3

from pathlib import Path

import orjson
from pystac import Asset, MediaType, Provider, ProviderRole
from stactools.usda_cdl import stac

root = Path(__file__).parents[1]
collection_path = root / "collection"
template_path = collection_path / "template.json"
description_path = collection_path / "description.md"

collection = stac.create_collection()
description = collection.description
collection.description = r"{{ collection.description }}"
collection.extra_fields.update(
    {
        "msft:short_description": (
            "The UDA Cropland Data Layer is an annual raster, geo-referenced, "
            "crop-specific land cover data layer produced using satellite "
            "imagery and extensive agricultural ground truth collected "
            "during the current growing season."
        ),
        "msft:storage_account": "landcoverdata",
        "msft:container": "usda-cdl",
        "msft:region": "westeurope",
    }
)
collection.providers.append(
    Provider(
        "Microsoft",
        None,
        [ProviderRole.HOST],
        "https://planetarycomputer.microsoft.com",
    )
)
collection.assets["thumbnail"] = Asset(
    href=(
        "https://ai4edatasetspublicassets.blob.core.windows.net"
        "/assets/pc_thumbnails/usda-cdl-thumb.png"
    ),
    title="USDA Cropland Data Layer (CDL) thumbnail",
    media_type=MediaType.PNG,
    roles=["thumbnail"],
)
collection.keywords = ["USDA", "United States", "Land Cover", "Land Use", "Agriculture"]

# Required until https://github.com/stac-utils/pystac/pull/896 is released
collection_as_dict = collection.to_dict(include_self_link=False)
collection_as_dict["links"] = [
    l for l in collection_as_dict["links"] if l["rel"] != "root"
]
collection_as_bytes = orjson.dumps(collection_as_dict, option=orjson.OPT_INDENT_2)
collection_path.mkdir(exist_ok=True)
with open(template_path, "wb") as f:
    f.write(collection_as_bytes)
with open(description_path, "w") as f:
    f.write(description)
