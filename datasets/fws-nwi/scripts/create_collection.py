#!/usr/bin/env python3

from pathlib import Path

import orjson
from pystac import Asset, MediaType, Provider, ProviderRole
from stactools.fws_nwi import stac

template_directory = Path(__file__).parents[1] / "collection"

collection = stac.create_collection()
description = collection.description
collection.description = "{{ collection.description }}"
collection.extra_fields[
    "msft:short_description"
] = "Vector dataset containing wetlands boundaries and identification across the United States."
collection.extra_fields["msft:storage_account"] = "ai4edataeuwest"
collection.extra_fields["msft:container"] = "fws-nwi"
collection.providers.append(
    Provider(
        "Microsoft",
        None,
        [ProviderRole.HOST],
        "https://planetarycomputer.microsoft.com",
    )
)
collection.assets["thumbnail"] = Asset(
    href="https://ai4edatasetspublicassets.blob.core.windows.net/assets/pc_thumbnails/fws-nwi-thumb.png",
    title="FWS National Wetlands Inventory thumbnail",
    media_type=MediaType.PNG,
    roles=["thumbnail"],
)
collection.keywords = ["USFWS", "Wetlands", "United States"]


# Required until https://github.com/stac-utils/pystac/pull/896 is released
collection_as_dict = collection.to_dict(include_self_link=False)
collection_as_dict["links"] = [
    l for l in collection_as_dict["links"] if l["rel"] != "root"
]
collection_as_bytes = orjson.dumps(collection_as_dict, option=orjson.OPT_INDENT_2)
with open(template_directory / "template.json", "wb") as f:
    f.write(collection_as_bytes)
with open(template_directory / "description.md", "w") as f:
    f.write(description)
