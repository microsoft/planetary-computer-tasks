from decimal import Decimal
from pathlib import Path
from typing import List, Union

import antimeridian
import pystac
import shapely.geometry

import pctasks.dataset.collection
from pctasks.core.models.task import WaitTaskResult
from pctasks.core.storage import StorageFactory


def nano2micro(value: float) -> float:
    # handles floating point arithmetic errors
    return float(Decimal(str(value)) / Decimal("1000"))


class Collection(pctasks.dataset.collection.Collection):
    @classmethod
    def create_item(
        cls, asset_uri: str, storage_factory: StorageFactory
    ) -> Union[List[pystac.Item], WaitTaskResult]:
        pass

        storage, json_path = storage_factory.get_storage_for_file(asset_uri)
        item_dict = storage.read_json(json_path)

        # Skip item if it is not a NT (Not Time critical) product.
        asset_directory = Path(item_dict["assets"]["safe-manifest"]["href"]).parent.name
        assert asset_directory.endswith(".SEN3")
        timeliness = asset_directory[-11:-9]
        assert timeliness in ["NR", "ST", "NT"]
        if asset_directory[-11:-9] != "NT":
            return []

        # ---- PROPERTIES ----
        properties = item_dict.pop("properties")

        # Add the processing timelessness to the properties
        properties["s3:processing_timeliness"] = timeliness

        # Providers should be supplied in the collection, not the item
        properties.pop("providers", None)

        # start_datetime and end_datetime are incorrectly formatted
        properties["start_datetime"] = pystac.utils.datetime_to_str(
            pystac.utils.str_to_datetime(properties["start_datetime"])
        )
        properties["end_datetime"] = pystac.utils.datetime_to_str(
            pystac.utils.str_to_datetime(properties["end_datetime"])
        )
        properties["datetime"] = pystac.utils.datetime_to_str(
            pystac.utils.str_to_datetime(properties["datetime"])
        )

        # "SYNERGY" is not a instrument
        properties.pop("instruments", None)

        # Do we really want to include s3:mode, which is set to EO (Earth
        # Observation)? It offers no additional information, IMO.
        properties.pop("s3:mode", None)

        # Do we really want to include s3:gsd for the OLCI and SLSTR
        # instruments? AOD is a derived product delivered at different resolution
        # than either the OLCI or SLSTR sensor GSDs. Also, s3:gsd is a *custom*
        # field with two gsd values that, IMO, is unlikely to be searched.
        properties.pop("s3:gsd", None)

        # Use underscores instead of camel case for consistency
        new_properties = {}
        for key in properties:
            if key.startswith("s3:"):
                new_key = "".join(
                    "_" + char.lower() if char.isupper() else char for char in key
                )
                # strip _pixels_percentages to match eo:cloud_cover pattern
                if new_key.endswith("_pixels_percentage"):
                    new_key = new_key.replace("_pixels_percentage", "")
                new_properties[new_key] = properties[key]
            else:
                new_properties[key] = properties[key]

        item_dict["properties"] = new_properties

        # ---- LINKS ----
        links = item_dict.pop("links")

        # license is the same for all items; include on the collection, not the item
        for link in links:
            if link["rel"] == "license":
                links.remove(link)

        item_dict["links"] = links

        # ---- ASSETS ----
        assets = item_dict.pop("assets")

        for key, value in assets.items():
            # remove local paths
            value.pop("file:local_path", None)

            # correct eo:bands
            if "eo:bands" in value:
                for band in value["eo:bands"]:
                    band["center_wavelength"] = nano2micro(band["center_wavelength"])
                    band["full_width_half_max"] = nano2micro(band["band_width"])
                    band.pop("band_width")

            # standardize the shape prefix to "s3:" across collections
            if "syn:shape" in value:
                value["s3:shape"] = value.pop("syn:shape")

            # make it clear that resolution is a custom field
            if "resolution" in value:
                value["s3:resolution"] = value.pop("resolution")

            # Add a description to the safe_manifest asset
            if key == "safe-manifest":
                value["description"] = "SAFE product manifest"

        item_dict["assets"] = assets

        # ---- GEOMETRY ----
        item = pystac.Item.from_dict(item_dict)
        polygon = shapely.geometry.shape(item.geometry)
        geometry = antimeridian.fix_polygon(polygon)
        item.bbox = list(geometry.bounds)
        item.geometry = shapely.geometry.mapping(geometry)

        return [item]


if __name__ == "__main__":
    c = Collection()
    asset_uri = "/Users/pjh/dev/planetary-computer-tasks/pjh/sentinel-3/S3A_SY_2_SYN_20180922T164930_20180922T165230_0180_036_083_3060.json"
    storage_factory = StorageFactory()
    item_list = c.create_item(asset_uri, storage_factory)

    import json

    with open(f"{asset_uri}.test.json", "w") as f:
        json.dump(item_list[0].to_dict(), f)
