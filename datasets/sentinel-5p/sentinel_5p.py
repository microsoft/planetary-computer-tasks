import logging
import re
from pathlib import Path
from typing import List, Union

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
    "aer_ai": "http://www.tropomi.eu/data-products/uv-aerosol-index",
    "aer_lh": "http://www.tropomi.eu/data-products/aerosol-layer-height",
    "ch4": "http://www.tropomi.eu/data-products/methane",
    "cloud": "http://www.tropomi.eu/data-products/cloud",
    "co": "http://www.tropomi.eu/data-products/carbon-monoxide",
    "hcho": "http://www.tropomi.eu/data-products/formaldehyde",
    "no2": "http://www.tropomi.eu/data-products/nitrogen-dioxide",
    "o3": "http://www.tropomi.eu/data-products/total-ozone-column",
    "o3_tcl": "http://www.tropomi.eu/data-products/tropospheric-ozone-column",
    "so2": "http://www.tropomi.eu/data-products/sulphur-dioxide",
    "npbd3": "https://sentinel.esa.int/web/sentinel/technical-guides/sentinel-5p/products-algorithms",  # noqa
    "npbd6": "https://sentinel.esa.int/web/sentinel/technical-guides/sentinel-5p/products-algorithms",  # noqa
    "npbd7": "https://sentinel.esa.int/web/sentinel/technical-guides/sentinel-5p/products-algorithms",  # noqa
}

ASSET_TITLES = {
    "aer_ai": "TROPOMI/S5P L2 Ultraviolet Aerosol Index",
    "aer_lh": "TROPOMI/S5P L2 Aerosol Layer Height",
    "ch4": "TROPOMI/S5P L2 Methane Total Column",
    "cloud": "TROPOMI/S5P L2 Cloud Fraction, Albedo, and Top Pressure",
    "co": "TROPOMI/S5P L2 Carbon Monoxide Total Column",
    "hcho": "TROPOMI/S5P L2 Formaldehyde Total Column",
    "no2": "TROPOMI/S5P L2 Nitrogen Dioxide Total Column",
    "o3": "TROPOMI/S5P L2 Ozone Total Column",
    "o3_tcl": "TROPOMI/S5P L2 Ozone Tropospheric Column",
    "so2": "TROPOMI/S5P L2 Sulphur Dioxide Total Column",
    "npbd3": "TROPOMI/S5P VIIRS/NPP Band 3 Cloud Mask",
    "npbd6": "TROPOMI/S5P VIIRS/NPP Band 6 Cloud Mask",
    "npbd7": "TROPOMI/S5P VIIRS/NPP Band 7 Cloud Mask",
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


class Sentinel5pNetCDFCollection(Collection):
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
        product = match.groupdict()["product"].strip("_").lower()
        if product.startswith("np"):
            product = product.replace("_", "")
        collection_identifier = match.groupdict()["collection"]

        # ---- PROPERTIES ----
        properties = item_dict.pop("properties")

        # providers should be supplied in the collection, not the item
        properties.pop("providers", None)

        # combine the product custom properties to a single object
        product_custom_fields = {}
        keys = [k for k in properties.keys() if str(k).startswith(product)]
        if keys:
            for key in keys:
                product_custom_fields[
                    str(key).replace(f"{product}:", "")
                ] = properties.pop(key)
            properties[f"s5p:{product}"] = product_custom_fields

        # add sentinel-5p collection_identifier
        properties["s5p:collection_identifier"] = collection_identifier

        # clean up spatial_resolution
        resolution = properties["s5p:spatial_resolution"]
        resolution = resolution.strip().strip("km2").strip("km").strip()
        parts = resolution.split("x")
        assert len(parts) == 2
        resolution = f"{float(parts[0])}x{float(parts[1])}km"
        properties["s5p:spatial_resolution"] = resolution

        # correct bad datetimes
        for k, v in properties.items():
            if k.endswith("datetime") and v.endswith("ZZ"):
                properties[k] = v[:-2] + "Z"
        if f"s5p:{product}" in properties:
            for k, v in properties[f"s5p:{product}"].items():
                if k.endswith("datetime") and v.endswith("ZZ"):
                    properties[f"s5p:{product}"][k] = v[:-2] + "Z"

        item_dict["properties"] = properties

        # ---- ASSETS ----
        asset = item_dict["assets"].pop("data")

        # the supplied asset description is too brief to be a description and
        # too inconsistent to use as a title; use a custom title instead
        asset.pop("description")
        asset["title"] = ASSET_TITLES[product]

        item_dict["assets"][product] = asset

        # ---- LINKS ----
        links = item_dict.pop("links")

        # license is the same for all items; include on the collection, not the item
        for link in links:
            if link["rel"] == "license":
                links.remove(link)

        # add a unique link to the product landing page
        about_href = ABOUT_LINKS.get(product)
        links.append(
            {
                "rel": "about",
                "href": about_href,
                "type": "text/html",
            }
        )

        item_dict["links"] = links

        # fix antimeridian, except for o3_tcl, where we do some hardcode hacks instead
        item = pystac.Item.from_dict(item_dict)
        if product == "o3_tcl":
            item.geometry = O3_TCL_GEOMETRY
            item.bbox = O3_TCL_BBOX
        else:
            polygon = shapely.geometry.shape(item.geometry)
            geometry = antimeridian.fix_polygon(polygon)
            item.bbox = list(geometry.bounds)
            item.geometry = shapely.geometry.mapping(geometry)

        return [item]
