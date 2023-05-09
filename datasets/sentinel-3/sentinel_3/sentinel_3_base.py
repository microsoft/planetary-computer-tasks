import logging
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional

import antimeridian
import pystac
import shapely.geometry
from sentinel_3.sentinel_3_winding import get_winding

import pctasks.dataset.collection

handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("[%(levelname)s]:%(asctime)s: %(message)s"))
handler.setLevel(logging.INFO)
logger = logging.getLogger(__name__)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

PRODUCT_NAMES = {
    "OL_2_LFR___": "olci-lfr",
    "OL_2_WFR___": "olci-wfr",
    "SL_2_FRP___": "slstr-frp",
    "SL_2_LST___": "slstr-lst",
    "SL_2_WST___": "slstr-wst",
    "SR_2_LAN___": "sral-lan",
    "SR_2_WAT___": "sral-wat",
    "SY_2_AOD___": "synergy-aod",
    "SY_2_SYN___": "synergy-syn",
    "SY_2_V10___": "synergy-v10",
    "SY_2_VG1___": "synergy-vg1",
    "SY_2_VGP___": "synergy-vgp",
}


def recursive_round(coordinates: List[Any], precision: int) -> List[Any]:
    """Rounds a list of numbers. The list can contain additional nested lists
    or tuples of numbers.

    Any tuples encountered will be converted to lists.

    Args:
        coordinates (List[Any]): A list of numbers, possibly containing nested
            lists or tuples of numbers.
        precision (int): Number of decimal places to use for rounding.

    Returns:
        List[Any]: The list of numbers rounded to the given precision.
    """
    rounded: List[Any] = []
    for value in coordinates:
        if isinstance(value, (int, float)):
            rounded.append(round(value, precision))
        else:
            rounded.append(recursive_round(list(value), precision))
    return rounded


def nano2micro(value: float) -> float:
    """Converts nanometers to micrometers while handling floating
    point arithmetic errors."""
    return float(Decimal(str(value)) / Decimal("1000"))


def hz2ghz(value: float) -> float:
    """Converts hertz to gigahertz while handling floating point
    arithmetic errors."""
    return float(Decimal(str(value)) / Decimal("1000000000"))


class BaseSentinelCollection(pctasks.dataset.collection.Collection):  # type: ignore
    def base_updates(item_dict: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Apply item updates.

        Args:
            item_dict (Dict[str, Any]): The Item dictionary as read from Azure.
            max_delta_lon (float): The maximum longitude difference used by
                the winding detection algorithm.

        Returns:
            Optional[Dict[str, Any]]: The updated Item dictionary, or None if
                the Item is not a NT (Not Time critical) product.
        """

        # Skip item if it is not a NT (Not Time critical) product.
        asset_directory = Path(item_dict["assets"]["safe-manifest"]["href"]).parent.name
        assert asset_directory.endswith(".SEN3")
        timeliness = asset_directory[-11:-9]
        assert timeliness in ["NR", "ST", "NT"]
        if asset_directory[-11:-9] != "NT":
            return None

        # Strip any trailing underscores from the ID
        original_id = item_dict["id"]
        item_dict["id"] = original_id.rstrip("_")

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

        # Add the processing timelessness to the properties
        properties["s3:processing_timeliness"] = timeliness

        # Add a user-friendly name
        properties["s3:product_name"] = PRODUCT_NAMES[properties["s3:productType"]]

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

        new_assets = {}
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
                asset["s3:altimetry_bands"] = asset.pop("sral:bands")
                for band in asset["s3:altimetry_bands"]:
                    band["frequency_band"] = band.pop("name")
                    band["center_frequency"] = hz2ghz(band.pop("central_frequency"))
                    band["band_width"] = hz2ghz(band.pop("band_width_in_Hz"))

            # Some titles are just the filenames
            if asset_key == "eopmetadata" or asset_key == "browse_jpg":
                asset.pop("title", None)

            # Make asset keys kebab-case
            new_asset_key = ""
            for first, second in zip(asset_key, asset_key[1:]):
                new_asset_key += first
                if first.islower() and second.isupper():
                    new_asset_key += "-"
            new_asset_key += asset_key[-1]
            new_asset_key = new_asset_key.replace("_", "-")
            new_asset_key = new_asset_key.lower()
            if asset_key == "eopmetadata":
                new_asset_key = "eop-metadata"
            new_assets[new_asset_key] = asset

        item_dict["assets"] = new_assets

        # ---- GEOMETRY ----
        geometry_dict = item_dict["geometry"]
        assert geometry_dict["type"] == "Polygon"

        if item_dict["properties"]["s3:product_name"] in [
            "synergy-v10",
            "synergy-vg1",
        ]:
            max_delta_lon = 300
        else:
            max_delta_lon = 120

        coords = geometry_dict["coordinates"][0]
        winding = get_winding(coords, max_delta_lon)
        if winding == "CW":
            geometry_dict["coordinates"][0] = coords[::-1]
        elif winding is None:
            logger.warning(
                f"Could not determine winding order of polygon in "
                f"Item: '{item_dict['id']}'"
            )

        geometry = shapely.geometry.shape(geometry_dict)

        # slstr-lst strip geometries are incorrect, so we apply a hack
        if item_dict["properties"][
            "s3:product_name"
        ] == "slstr-lst" and original_id.endswith("_____"):
            geometry = antimeridian.fix_polygon(geometry, force_north_pole=True)
        else:
            geometry = antimeridian.fix_polygon(geometry)

        if not geometry.is_valid:
            geometry = geometry.buffer(0)

        item_dict["bbox"] = list(geometry.bounds)
        item_dict["geometry"] = shapely.geometry.mapping(geometry)
        item_dict["geometry"]["coordinates"] = recursive_round(
            list(item_dict["geometry"]["coordinates"]), precision=4
        )
        item_dict["bbox"] = recursive_round(list(item_dict["bbox"]), precision=4)

        return item_dict
