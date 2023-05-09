import logging
import re
from pathlib import Path
from typing import Any, List, Union

import antimeridian
import pystac
import shapely.geometry
from shapely.geometry import Polygon

from pctasks.core.models.task import WaitTaskResult
from pctasks.core.storage import StorageFactory
from pctasks.dataset.collection import Collection

FILENAME_EXPR = re.compile(
    r"S5P_(?P<mode>[A-Z]{4})_L(?P<level>[0-9]{1})_(?P<product>.{7})_"
    r"(?P<start_datetime>[0-9,A-Z]{15})_(?P<end_datetime>[0-9,A-Z]{15})_"
    r"(?P<orbit>[0-9]{5})_(?P<collection>[0-9]{2})_(?P<processor_version>[0-9]{6})_"
    r"(?P<production_datetime>[0-9,A-Z]{15})"
)

ABOUT_LINKS = {
    "L2__AER_AI": "http://www.tropomi.eu/data-products/uv-aerosol-index",
    "L2__AER_LH": "http://www.tropomi.eu/data-products/aerosol-layer-height",
    "L2__CH4___": "http://www.tropomi.eu/data-products/methane",
    "L2__CLOUD_": "http://www.tropomi.eu/data-products/cloud",
    "L2__CO____": "http://www.tropomi.eu/data-products/carbon-monoxide",
    "L2__HCHO__": "http://www.tropomi.eu/data-products/formaldehyde",
    "L2__NO2___": "http://www.tropomi.eu/data-products/nitrogen-dioxide",
    "L2__O3____": "http://www.tropomi.eu/data-products/total-ozone-column",
    "L2__O3_TCL": "http://www.tropomi.eu/data-products/tropospheric-ozone-column",
    "L2__SO2___": "http://www.tropomi.eu/data-products/sulphur-dioxide",
    "L2__NP_BD3": "https://sentinel.esa.int/web/sentinel/technical-guides/sentinel-5p/products-algorithms",  # noqa
    "L2__NP_BD6": "https://sentinel.esa.int/web/sentinel/technical-guides/sentinel-5p/products-algorithms",  # noqa
    "L2__NP_BD7": "https://sentinel.esa.int/web/sentinel/technical-guides/sentinel-5p/products-algorithms",  # noqa
}

ASSET_TITLES = {
    "L2__AER_AI": "Ultraviolet Aerosol Index",
    "L2__AER_LH": "Aerosol Layer Height",
    "L2__CH4___": "Methane Total Column",
    "L2__CLOUD_": "Cloud Fraction, Albedo, and Top Pressure",
    "L2__CO____": "Carbon Monoxide Total Column",
    "L2__HCHO__": "Formaldehyde Total Column",
    "L2__NO2___": "Nitrogen Dioxide Total Column",
    "L2__O3____": "Ozone Total Column",
    "L2__O3_TCL": "Ozone Tropospheric Column",
    "L2__SO2___": "Sulphur Dioxide Total Column",
    "L2__NP_BD3": "VIIRS/NPP Band 3 Cloud Mask",
    "L2__NP_BD6": "VIIRS/NPP Band 6 Cloud Mask",
    "L2__NP_BD7": "VIIRS/NPP Band 7 Cloud Mask",
}

O3_TCL_GEOMETRY = shapely.geometry.mapping(
    Polygon([(-180, -19.75), (180, -19.75), (180, 19.75), (-180, 19.75)])
)
O3_TCL_BBOX = [-180, -19.75, 180, 19.75]

handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("[%(levelname)s]:%(asctime)s: %(message)s"))
handler.setLevel(logging.INFO)
logger = logging.getLogger(__name__)
logger.addHandler(handler)
logger.setLevel(logging.INFO)


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


class Sentinel5pNetCDFCollection(Collection):  # type: ignore
    @classmethod
    def create_item(
        cls, asset_uri: str, storage_factory: StorageFactory
    ) -> Union[List[pystac.Item], WaitTaskResult]:

        storage, json_path = storage_factory.get_storage_for_file(asset_uri)
        item_dict = storage.read_json(json_path)

        netcdf_filename = item_dict["assets"]["data"]["href"]
        match = FILENAME_EXPR.match(Path(netcdf_filename).stem)
        if not match:
            raise ValueError(f"Could not parse filename {Path(json_path).stem}")

        prefix = match.groupdict()["product"].strip("_").lower()
        if prefix.startswith("np"):
            prefix = prefix.replace("_", "")

        collection_identifier = match.groupdict()["collection"]
        product_type = item_dict["properties"]["s5p:product_type"]
        product_name = product_type.lstrip("L2_").rstrip("_").lower().replace("_", "-")

        # ---- PROPERTIES ----
        properties = item_dict.pop("properties")

        # providers should be supplied in the collection, not the item
        properties.pop("providers", None)

        # combine the product custom properties to a single object
        product_custom_fields = {}
        keys = [k for k in properties.keys() if str(k).startswith(prefix)]
        if keys:
            for key in keys:
                product_custom_fields[
                    str(key).replace(f"{prefix}:", "")
                ] = properties.pop(key)
            properties[f"s5p:{prefix}"] = product_custom_fields

        # add sentinel-5p collection_identifier
        properties["s5p:collection_identifier"] = collection_identifier

        # convert spatial resolution to meters, store in list to match sentinel-3
        # order is [height, width], aka [along track, across track]
        resolution = properties["s5p:spatial_resolution"]
        resolution = resolution.strip().strip("km2").strip("km").strip()
        parts = resolution.split("x")
        assert len(parts) == 2
        properties["s5p:spatial_resolution"] = [int(float(p)) * 1000 for p in parts]

        # correct bad datetimes
        for k, v in properties.items():
            if k.endswith("datetime") and v.endswith("ZZ"):
                properties[k] = v[:-2] + "Z"
        if f"s5p:{prefix}" in properties:
            for k, v in properties[f"s5p:{prefix}"].items():
                if k.endswith("datetime") and v.endswith("ZZ"):
                    properties[f"s5p:{prefix}"][k] = v[:-2] + "Z"

        # add a user-friendly product name
        properties["s5p:product_name"] = product_name

        item_dict["properties"] = properties

        # ---- ASSETS ----
        asset = item_dict["assets"].pop("data")

        # the supplied asset description is too brief to be a description and
        # too inconsistent to use as a title; use a custom title instead
        asset.pop("description")
        asset["title"] = ASSET_TITLES[product_type]

        item_dict["assets"][product_name] = asset

        # ---- LINKS ----
        links = item_dict.pop("links")

        # license is the same for all items; include on the collection, not the item
        for link in links:
            if link["rel"] == "license":
                links.remove(link)

        # add a unique link to the product landing page
        links.append(
            {
                "rel": "about",
                "href": ABOUT_LINKS.get(product_type),
                "type": "text/html",
            }
        )

        item_dict["links"] = links

        # ---- GEOMETRY ----
        # fix antimeridian, except for o3_tcl, where we do some hardcode hacks instead
        item = pystac.Item.from_dict(item_dict)
        if product_name == "o3-tcl":
            item.geometry = O3_TCL_GEOMETRY
            item.bbox = O3_TCL_BBOX
        else:
            polygon = shapely.geometry.shape(item.geometry)
            geometry = antimeridian.fix_polygon(polygon)
            item.bbox = list(geometry.bounds)
            item.geometry = shapely.geometry.mapping(geometry)
            item.bbox = recursive_round(item.bbox, precision=6)
            item.geometry["coordinates"] = recursive_round(  # type: ignore
                list(item.geometry["coordinates"]), precision=6  # type: ignore
            )

        return [item]
