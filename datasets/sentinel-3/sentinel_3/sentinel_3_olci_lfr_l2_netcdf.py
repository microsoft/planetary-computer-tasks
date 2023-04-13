import decimal
from typing import List, Union

import pystac

import pctasks.dataset.collection
from pctasks.core.models.task import WaitTaskResult
from pctasks.core.storage import StorageFactory


class Collection(pctasks.dataset.collection.Collection):
    @classmethod
    def create_item(
        cls, asset_uri: str, storage_factory: StorageFactory
    ) -> Union[List[pystac.Item], WaitTaskResult]:
 
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

        # FIXME: Do we really want to include s3:mode, which is set to EO
        # (Earth Observation)? It offers no additional information, IMO.
        properties.pop("s3:mode", None)

        # FIXME: Do we really want to include s3:gsd for the OLCI and SLSTR
        # instruments? This is a custom object that is unlikely to be searched.
        properties.pop("s3:gsd", None)

        # FIXME: Use underscores instead of camel case for consistency

        properties["s3:product_type"] = properties.pop("s3:productType")
        properties["s3:saline_water_pixels_percentage"] = properties.pop(
            "s3:salineWaterPixels_percentage"
        )
        properties["s3:coastal_pixels_percentage"] = properties.pop(
            "s3:coastalPixels_percentage"
        )
        properties["s3:fresh_inland_water_pixels_percentage"] = properties.pop(
            "s3:freshInlandWaterPixels_percentage"
        )
        properties["s3:tidal_region_pixels_percentage"] = properties.pop(
            "s3:tidalRegionPixels_percentage"
        )
        properties["s3:land_pixels_percentage"] = properties.pop(
            "s3:landPixels_percentage"
        )
        # FIXME: Use `raster:valid_percent`?
        properties["s3:invalid_pixels_percentage"] = properties.pop(
            "s3:invalidPixels_percentage"
        )
        properties["s3:cosmetic_pixels_percentage"] = properties.pop(
            "s3:cosmeticPixels_percentage"
        )
        properties["s3:duplicated_pixels_percentage"] = properties.pop(
            "s3:duplicatedPixels_percentage"
        )
        properties["s3:saturated-pixels_percentage"] = properties.pop(
            "s3:saturatedPixels_percentage"
        )
        properties["s3:dubious-samples_percentage"] = properties.pop(
            "s3:dubiousSamples_percentage"
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

        # FIXME: are we going camelCase -> snake-case for asset keys?
        # FIXME: Make asset slugs consistent (underscores and lowercase)
        assets["safe_manifest"] = assets.pop("safe-manifest")
        assets["safe_manifest"]["title"] = "SAFE product manifest"

        resolutions = set()

        for k, v in assets.items():
            # Remove file:local_path
            v.pop("file:local_path", None)

            # Move description to title
            title = v.pop("description", None)
            if title:
                v["title"] = title

            resolution = v.pop("resolution", None)
            if resolution:
                resolutions.add(tuple(resolution))

            # eo:bands requires the wavelenth in micrometers. These are nanometers.
            eo_bands = v.get("eo:bands", [])
            for band in eo_bands:
                for eo_key in ["band_width", "center_wavelength"]:
                    band[eo_key] = float(decimal.Decimal(band[eo_key]) / 1000)

        item_dict["assets"] = assets

        # FIXME: There is a lonely "resolution" field on the ntc_aod asset that
        # is not part of the STAC spec. This would normally go in "raster:bands",
        # but we are not using that extension. Propose moving this to Item
        # properties under "s3:spatial_resolution", which matches Sentinel-5P.
        assert len(resolutions) == 1, len(resolutions)
        parts = resolutions.pop()
        assert len(parts) == 2, len(parts)
        resolution = f"{float(parts[0])}x{float(parts[1])}m"
        properties["s3:spatial_resolution"] = resolution

        item = pystac.Item.from_dict(item_dict)
        return [item]


if __name__ == "__main__":
    c = Collection()
    asset_uri = "blob://sentinel3euwest/sentinel-3-stac/OLCI/OL_2_LFR___/2023/04/01/S3A_OL_2_LFR_20230401T004527_20230401T004655_0088_097_145_1440.json"
    storage_factory = StorageFactory()
    c.create_item(asset_uri, storage_factory)
