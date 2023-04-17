from pathlib import Path
from typing import List, Union

import antimeridian
import pystac
import shapely.geometry

import pctasks.dataset.collection
from pctasks.core.models.task import WaitTaskResult
from pctasks.core.storage import StorageFactory


class Collection(pctasks.dataset.collection.Collection):
    @classmethod
    def create_item(
        cls, asset_uri: str, storage_factory: StorageFactory
    ) -> Union[List[pystac.Item], WaitTaskResult]:
        pass

        storage, json_path = storage_factory.get_storage_for_file(asset_uri)
        item_dict = storage.read_json(json_path)

        # Skip item if it is not a NT (Not Time critical) product
        asset_directory = Path(item_dict["assets"]["safe-manifest"]["href"]).parent.name
        assert asset_directory.endswith(".SEN3")
        timeliness = asset_directory[-11:-9]
        assert timeliness in ["NR", "ST", "NT"]
        if asset_directory[-11:-9] != "NT":
            return []

        # Item id contains trailing underscores to pad out a 17 character
        # instance id
        item_dict["id"] = item_dict["id"].rstrip("_")

        # ---- PROPERTIES ----
        properties = item_dict.pop("properties")

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

        # I'm not sure what to do with the s3:shape information. It would
        # normally be included in the proj extension, but we are not including
        # that extension. I see the synergy-syn product uses a syn:shape field
        # in a different format on the asset. So there is no consistency. I'm
        # moving it to the asset as a custom field for now, with the intent to
        # match this layout in all the synergy products.
        shape = properties.pop("s3:shape")

        # Use underscores instead of camel case for consistency
        new_properties = {}
        for key in properties:
            if key.startswith("s3:"):
                new_key = "".join(
                    "_" + char.lower() if char.isupper() else char for char in key
                )
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

        # Make asset slugs consistent (underscores and lowercase)
        new_assets = {}
        for key in assets:
            new_key = key.lower().replace("-", "_")
            new_assets[new_key] = assets[key]
        assets = new_assets

        # Remove local_path and clean up descriptions
        assets["safe_manifest"]["description"] = "SAFE product manifest"
        assets["safe_manifest"].pop("file:local_path", None)

        assets["ntc_aod"][
            "description"
        ] = "Global aerosol parameters and surface reflectance"
        assets["ntc_aod"].pop("file:local_path", None)

        # Add the custom shape field we peeled off the properties
        assets["ntc_aod"]["s3:shape"] = shape

        # Make it clear that resolution is a custom field
        assets["ntc_aod"]["s3:resolution"] = assets["ntc_aod"].pop("resolution")

        # The eo:bands data should be in micrometers (it is in nanometers)
        for band in assets["ntc_aod"]["eo:bands"]:
            band["center_wavelength"] = band["center_wavelength"] / 1000
            band["full_width_half_max"] = band["band_width"] / 1000
            band.pop("band_width")

        item_dict["assets"] = assets

        # ---- GEOMETRY ----
        item = pystac.Item.from_dict(item_dict)
        polygon = shapely.geometry.shape(item.geometry)
        geometry = antimeridian.fix_polygon(polygon)
        item.bbox = list(geometry.bounds)
        item.geometry = shapely.geometry.mapping(geometry)

        return [item]
