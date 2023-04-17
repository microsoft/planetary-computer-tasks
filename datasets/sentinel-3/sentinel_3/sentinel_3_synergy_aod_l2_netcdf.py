from typing import List, Union

import pystac

import pctasks.dataset.collection
from pctasks.core.models.task import WaitTaskResult
from pctasks.core.storage import StorageFactory


class SynergyAODCollection(pctasks.dataset.collection.Collection):
    @classmethod
    def create_item(
        cls, asset_uri: str, storage_factory: StorageFactory
    ) -> Union[List[pystac.Item], WaitTaskResult]:
        pass

        storage, json_path = storage_factory.get_storage_for_file(asset_uri)
        item_dict = storage.read_json(json_path)

        # FIXME: Item id contains trailing underscores to pad out a 17 character
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

        # FIXME: "SYNERGY" is not a instrument
        properties.pop("instrument", None)

        # FIXME: Do we really want to include s3:mode, which is set to EO
        # (Earth Observation)? It offers no additional information, IMO.
        properties.pop("s3:mode", None)

        # FIXME: Do we really want to include s3:gsd for the OLCI and SLSTR
        # instruments? This is a custom object that is unlikely to be searched.
        properties.pop("s3:gsd", None)

        # FIXME: Use underscores instead of camel case for consistency
        properties["sd:product_type"] = properties.pop("sd:productType")
        properties["s3:saline_water_pixels_percentage"] = properties.pop(
            "s3:salineWaterPixels_percentage"
        )
        properties["s3:land_pixels_percentage"] = properties.pop(
            "s3:landPixels_percentage"
        )

        item_dict["properties"] = properties

        # ---- LINKS ----
        links = item_dict.pop("links")

        # license is the same for all items; include on the collection, not the item
        for link in links:
            if link["rel"] == "license":
                links.remove(link)

        item_dict["links"] = links

        # ---- ASSETS ----
        assets = item_dict.pop("assets")

        # FIXME: Make asset slugs consistent (underscores and lowercase)
        assets["safe_manifest"] = assets.pop("safe-manifest")
        assets["ntc_aod"] = assets.pop("NTC_AOD")

        # Remove local_path and clean up titles
        assets["safe_manifest"]["title"] = "SAFE product manifest"
        assets["safe_manifest"].pop("file:local_path", None)
        assets["ntc_aod"]["title"] = "Surface Reflectance and Global Aerosol Parameter"
        assets["ntc_aod"].pop("description", None)
        assets["ntc_aod"].pop("file:local_path", None)

        # FIXME: Since this is an Aerosol product (that includes reflectance
        # data), it seems odd to include include eo:bands. But I could be
        # persuaded otherwise.
        assets["ntc_aod"].pop("eo:bands", None)

        # FIXME: There is a lonely "resolution" field on the ntc_aod asset that
        # is not part of the STAC spec. This would normally go in "raster:bands",
        # but we are not using that extension. Propose moving this to Item
        # properties under "s3:spatial_resolution", which matches Sentinel-5P.
        spatial_resolution = assets["ntc_aod"].pop("resolution")
        assert len(spatial_resolution) == 2
        item_dict["properties"]["s3:spatial_resolution"] = f"{spatial_resolution[0]}m"

        item_dict["assets"] = assets

        # TODO: Fix geometry

        return [pystac.Item.from_dict(item_dict)]
