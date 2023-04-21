from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, Optional

import antimeridian
import pystac
import shapely.geometry

import pctasks.dataset.collection


class BaseSentinelCollection(pctasks.dataset.collection.Collection):  # type: ignore
    def base_updates(
        item_dict: Dict[str, Any], fix_geometry: bool = False, buffer0: bool = False
    ) -> Optional[Dict[str, Any]]:
        """Apply item updates.

        Args:
            item_dict (Dict[str, Any]): The Item dictionary as read from Azure.
            fix_geometry (bool): If True, fix the Item geometry so that it
                splits on the antimeridian and encompasses the poles if
                required. Defaults to False.
            buffer0 (bool): If True, correct any self-intersection in the Item
                geometry. Defaults to False.

        Returns:
            Optional[Dict[str, Any]]: The updated Item dictionary, or None if
                the Item is not a NT (Not Time critical) product.
        """

        def nano2micro(value: float) -> float:
            """Converts nanometers to micrometers while handling floating
            point arithmetic errors."""
            return float(Decimal(str(value)) / Decimal("1000"))

        def hz2ghz(value: float) -> float:
            """Converts hertz to gigahertz while handling floating point
            arithmetic errors."""
            return float(Decimal(str(value)) / Decimal("1000000000"))

        # Skip item if it is not a NT (Not Time critical) product.
        asset_directory = Path(item_dict["assets"]["safe-manifest"]["href"]).parent.name
        assert asset_directory.endswith(".SEN3")
        timeliness = asset_directory[-11:-9]
        assert timeliness in ["NR", "ST", "NT"]
        if asset_directory[-11:-9] != "NT":
            return None

        # Strip any trailing underscores from the ID
        item_dict["id"] = item_dict["id"].rstrip("_")

        # ---- PROPERTIES ----
        properties = item_dict.pop("properties")

        # Update placeholder platform ID to the final version
        sat_id = "sat:platform_international_designator"
        if properties[sat_id] == "0000-000A":
            properties[sat_id] = "2016-011A"
        elif properties[sat_id] == "0000-000B":
            properties[sat_id] = "2018-039A"

        if properties["instruments"] == ["SYNERGY"]:
            # "SYNERGY" is not a instrument
            properties["instruments"] = ["OLCI", "SLSTR"]

        # The gsd field does not align with the STAC spec, but it does contain
        # correct information on the different sensor gsd values. Leaving for now.
        # properties.pop("s3:gsd", None)

        # Add the processing timelessness to the properties
        properties["s3:processing_timeliness"] = timeliness

        # Add a user-friendly name
        properties["s3:product_name"] = (
            properties["s3:productType"].rstrip("_").split("_")[-1]
        )

        # Providers should be supplied in the Collection, not the Item
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

        # Remove s3:mode, which is always set to EO (Earth # Observation). It
        # offers no additional information.
        properties.pop("s3:mode", None)

        # Use underscores instead of camel case for consistency
        new_properties = {}
        for key in properties:
            if key.startswith("s3:"):
                new_key = "".join(
                    "_" + char.lower() if char.isupper() else char for char in key
                )
                # strip "_pixels_percentages" to match eo:cloud_cover pattern
                if new_key.endswith("_pixels_percentage"):
                    new_key = new_key.replace("_pixels_percentage", "")
                elif new_key.endswith("_pixelss_percentage"):
                    new_key = new_key.replace("_pixelss_percentage", "")
                elif new_key.endswith("_percentage"):
                    new_key = new_key.replace("_percentage", "")
                new_properties[new_key] = properties[key]
            else:
                new_properties[key] = properties[key]

        item_dict["properties"] = new_properties

        # ---- LINKS ----
        links = item_dict.pop("links")

        # license is the same for all Items; include on the Collection, not the Item
        for link in links:
            if link["rel"] == "license":
                links.remove(link)

        item_dict["links"] = links

        # ---- ASSETS ----
        assets = item_dict.pop("assets")

        for asset_key, asset in assets.items():
            # remove local paths
            asset.pop("file:local_path", None)

            # Add a description to the safe_manifest asset
            if asset_key == "safe-manifest":
                asset["description"] = "SAFE product manifest"

            # correct eo:bands
            if "eo:bands" in asset:
                for band in asset["eo:bands"]:
                    band["center_wavelength"] = nano2micro(band["center_wavelength"])
                    band["full_width_half_max"] = nano2micro(band["band_width"])
                    band.pop("band_width")

            # Tune up the radar altimetry bands. Radar altimetry is different
            # enough than radar imagery that the existing SAR extension doesn't
            # quite work (plus, the SAR extension doesn't have a band object).
            # We'll use a band construct similar to eo:bands, but follow the
            # naming and unit conventions in the SAR extension.
            if "sral:bands" in asset:
                asset["s3:radar_bands"] = asset.pop("sral:bands")
                for band in asset["s3:radar_bands"]:
                    band["frequency_band"] = band.pop("name")
                    band["center_frequency"] = hz2ghz(band.pop("central_frequency"))
                    band["band_width"] = hz2ghz(band.pop("band_width_in_Hz"))

        item_dict["assets"] = assets

        # ---- GEOMETRY ----
        if fix_geometry:
            geometry_dict = item_dict["geometry"]
            assert geometry_dict["type"] == "Polygon"
            geometry = shapely.geometry.shape(geometry_dict)
            geometry = antimeridian.fix_polygon(geometry)
            if buffer0:
                geometry = geometry.buffer(0)
            item_dict["bbox"] = list(geometry.bounds)
            item_dict["geometry"] = shapely.geometry.mapping(geometry)

        return item_dict
