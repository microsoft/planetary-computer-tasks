from typing import List, Union

import orjson
import pystac

from pctasks.core.models.task import WaitTaskResult
from pctasks.core.storage import StorageFactory
from pctasks.dataset.collection import Collection
# from pctasks.core.pctasks.core.models.task import WaitTaskResult
# from pctasks.core.pctasks.core.storage import StorageFactory
# from pctasks.dataset.pctasks.dataset.collection import Collection


ASSET_INFO = {
    "vv": {
        "title": "VV: vertical transmit, vertical receive",
        "description": (
            "Amplitude of signal transmitted with "
            "vertical polarization and received with vertical polarization "
            "with radiometric terrain correction applied."
        ),
    },
    "vh": {
        "title": "VH: vertical transmit, horizontal receive",
        "description": (
            "Amplitude of signal transmitted with "
            "vertical polarization and received with horizontal polarization "
            "with radiometric terrain correction applied."
        ),
    },
    "hh": {
        "title": "HH: horizontal transmit, horizontal receive",
        "description": (
            "Amplitude of signal transmitted with "
            "horizontal polarization and received with horizontal polarization "
            "with radiometric terrain correction applied."
        ),
    },
    "hv": {
        "title": "HV: horizontal transmit, vertical receive",
        "description": (
            "Amplitude of signal transmitted with "
            "horizontal polarization and received with vertical polarization "
            "with radiometric terrain correction applied."
        ),
    },
}


class S1GRDCollection(Collection):  # type: ignore
    @classmethod
    def create_item(
        cls, asset_uri: str, storage_factory: StorageFactory
    ) -> Union[List[pystac.Item], WaitTaskResult]:

        storage, path = storage_factory.get_storage_for_file(asset_uri)
        item_dict = orjson.loads(storage.read_bytes(path))

        item = pystac.Item.from_dict(item_dict, preserve_dict=False)

        # Remove providers
        item.properties.pop("providers", None)

        # Remove eo:bands from assets; fix-up titles and descriptions
        for asset_key, asset in item.assets.items():
            if asset_key in ASSET_INFO:
                _ = asset.extra_fields.pop("eo:bands", None)
                asset.title = ASSET_INFO[asset_key]["title"]
                asset.description = ASSET_INFO[asset_key]["description"]

        # Remove EO extension
        item.stac_extensions = [ext for ext in item.stac_extensions if "/eo/" not in ext]

        # Convert multipolygons to polygons if possible
        assert item.geometry
        if item.geometry["type"] == "MultiPolygon":
            if len(item.geometry["coordinates"]) == 1:
                item.geometry["coordinates"] = item.geometry["coordinates"][0]
                item.geometry["type"] = "Polygon"
            else:
                # Multipolygons are used to handle antimeridian crossing
                pass

        return [item]


if __name__ == "__main__":
    hrefs = [
        "/Users/pjh/data/sentinel-1/grd/catalyst/S1A_EW_GRDM_1SDH_20230501T021635_20230501T021740_048334_05D023.json"
    ]
    for href in hrefs:
        storage_factory = StorageFactory()
        c = S1GRDCollection()
        item = c.create_item(href, storage_factory)[0]
        item.validate()
        import json
        with open(f"{item.id}.json", "w") as f:
            json.dump(item.to_dict(), f, indent=4)