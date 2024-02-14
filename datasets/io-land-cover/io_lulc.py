from abc import abstractmethod
from functools import lru_cache
from typing import Dict, List, Union

import orjson
import pystac
import rasterio
from pystac.extensions.file import FileExtension, MappingObject
from pystac.extensions.label import LabelClasses, LabelExtension, LabelType
from pystac.extensions.projection import ProjectionExtension
from pystac.extensions.raster import RasterBand, RasterExtension
from pystac.utils import datetime_to_str, str_to_datetime

from pctasks.core.models.task import WaitTaskResult
from pctasks.core.storage import StorageFactory
from pctasks.dataset.collection import Collection

IO_LULC = "io-lulc"
IO_LULC_9_CLASS = "io-lulc-9-class"
IO_LULC_ANNUAL_V02 = "io-lulc-annual-v02"

IO_LULC_10_CLASS_ITEMS = (
    "blob://ai4edataeuwest/io-lulc/io-lulc-model-001-"
    "v01-composite-v03-supercell-v02-clip-v01.geojson"
)

IO_LULC_9_CLASS_2017_2021_ITEMS = (
    "blob://ai4edataeuwest/io-lulc/io-lulc-model-001-"
    "v02-composite-v01-supercell-v02-clip-v01.geojson"
)

IO_LULC_9_CLASS_2022_ITEMS = (
    "blob://ai4edataeuwest/io-lulc/io-lulc-model-001-"
    "v02-composite-v01-supercell-v02-clip-v01_2022_addition.geojson"
)

IO_LULC_ANNUAL_V02_ITEMS = (
    "blob://ai4edataeuwest/io-lulc/io-lulc-annual-v02-2017-2023.ndjson"
)

ASSET_KEY = "data"

NINE_CLASS_2017_2021_VSIAZ_PREFIX = (
    "/vsiaz/io-lulc/io-lulc-model-001/v02/supercells/"
    "io-lulc-model-001-v02-composite-v01-supercell-v02-clip-v01"
)

NINE_CLASS_2022_VSIAZ_PREFIX = "/vsiaz/io-msft-lulc"

IO_LULC_ANNUAL_V02_VSIAZ_PREFIXES = [
    "/vsiaz/io-annual-lulc-v02",
    "/vsiaz/maps-for-good-esri",
]


class IOItems:
    @classmethod
    @lru_cache(maxsize=1)
    def get(
        cls, storage_factory: StorageFactory, collection: str
    ) -> Dict[str, pystac.Item]:
        def _read_item_collection(uri: str) -> pystac.ItemCollection:
            storage, path = storage_factory.get_storage_for_file(uri)
            if uri.lower().endswith(".ndjson"):
                return pystac.ItemCollection(storage.read_ndjson(path))
            else:
                return pystac.ItemCollection.from_dict(
                    orjson.loads(storage.read_bytes(path))
                )

        result = {}

        if collection == IO_LULC:
            item_collection = _read_item_collection(IO_LULC_10_CLASS_ITEMS)
            for item in item_collection.items:
                asset = item.assets["supercell"]

                # 2020 10-class
                path = "/".join(asset.href.split("/")[-2:])

                result[path] = item
        elif collection == IO_LULC_9_CLASS:
            # 2017-2021
            item_collection_2017_2021 = _read_item_collection(
                IO_LULC_9_CLASS_2017_2021_ITEMS
            )
            for item in item_collection_2017_2021.items:
                asset = item.assets["supercell"]

                path = asset.href.replace(
                    NINE_CLASS_2017_2021_VSIAZ_PREFIX, "nine-class"
                )

                result[path] = item

            # 2022
            item_collection_2022 = _read_item_collection(IO_LULC_9_CLASS_2022_ITEMS)
            for item in item_collection_2022.items:
                asset = item.assets["supercell"]

                path = asset.href.replace(NINE_CLASS_2022_VSIAZ_PREFIX, "nine-class")

                # Only take 2022 items
                if path.endswith("20230101.tif"):
                    result[path] = item
        elif collection == IO_LULC_ANNUAL_V02:
            item_collection = _read_item_collection(IO_LULC_ANNUAL_V02_ITEMS)
            for item in item_collection.items:
                if "supercell" in item.assets:
                    asset = item.assets["supercell"]
                elif "data" in item.assets:
                    asset = item.assets["data"]
                else:
                    raise ValueError("Unknown asset property")

                path = asset.href
                for prefix in IO_LULC_ANNUAL_V02_VSIAZ_PREFIXES:
                    path = path.replace(prefix, "io-annual-lulc-v02")

                print(f"Adding {path} to result.")
                result[path] = item
        else:
            raise ValueError(f"Unknown collection: {collection}")

        return result


class BaseIOCollection(Collection):
    collection: str

    @classmethod
    @abstractmethod
    def apply_classmap(cls, item: pystac.Item, asset: pystac.Asset) -> None:
        pass

    @classmethod
    def create_item(
        cls, asset_uri: str, storage_factory: StorageFactory
    ) -> Union[List[pystac.Item], WaitTaskResult]:
        io_items = IOItems.get(storage_factory, cls.collection)

        asset_storage, tif_path = storage_factory.get_storage_for_file(asset_uri)
        tif_href = asset_storage.get_authenticated_url(tif_path)
        print(f"io_items has {len(io_items)} items.")
        io_item = io_items[tif_path]
        id_parts = io_item.id.split("_")

        if io_item.id.count("_") == 1:
            # Example: 60W_20220101-20230101
            tile_id = id_parts[0]
            year = id_parts[1][:4]
        else:
            # Example: io-lulc-model-001-v02-composite-v01-supercell-v02-clip-v01_60W_20190101-20200101
            tile_id = id_parts[1]
            year = id_parts[2][:4]

        item_id = f"{tile_id}-{year}"

        # Avoid 21V, as it is empty
        if item_id.startswith("21V-"):
            return []

        item = pystac.Item(
            id=item_id,
            datetime=None,
            geometry=io_item.geometry,
            bbox=io_item.bbox,
            properties={
                "start_datetime": datetime_to_str(str_to_datetime(f"{year}-01-01")),
                "end_datetime": datetime_to_str(
                    str_to_datetime(f"{int(year)+1}-01-01")
                ),
            },
        )

        asset = pystac.Asset(
            href=asset_storage.get_url(tif_path),
            media_type=pystac.MediaType.COG,
            roles=["data"],
        )
        item.add_asset(ASSET_KEY, asset)
        if "io:supercell_id" in io_item.properties:
            item.properties["io:supercell_id"] = io_item.properties["io:supercell_id"]
        elif "supercell" in io_item.properties:
            item.properties["supercell"] = io_item.properties["supercell"]

        item.properties["io:tile_id"] = tile_id

        # Projection Extension

        proj_ext = ProjectionExtension.ext(item, add_if_missing=True)

        with rasterio.open(tif_href) as ds:
            proj_ext.epsg = ds.crs.to_epsg()
            proj_ext.bbox = list(ds.bounds)
            proj_ext.transform = list(ds.transform)[:6]
            proj_ext.shape = list(ds.shape)

        cls.apply_classmap(item, asset)

        # File extension
        file_ext = FileExtension.ext(asset, add_if_missing=True)
        info = asset_storage.get_file_info(tif_path)
        file_ext.size = info.size

        # Raster Extension
        RasterExtension.add_to(item)
        raster_ext = RasterExtension.ext(asset)
        raster_ext.apply(bands=[RasterBand.create(spatial_resolution=10, nodata=0)])

        return [item]


class TenClassIOCollection(BaseIOCollection):
    collection = IO_LULC

    @classmethod
    def apply_classmap(cls, item: pystac.Item, asset: pystac.Asset) -> None:
        # Label Extension

        label_ext = LabelExtension.ext(item, add_if_missing=True)

        label_ext.apply(
            label_description="lulc",
            label_type=LabelType.RASTER,
            label_classes=[
                LabelClasses.create(
                    classes=[
                        "nodata",
                        "water",
                        "trees",
                        "grass",
                        "flooded veg",
                        "crops",
                        "scrub",
                        "built area",
                        "bare",
                        "snow/ice",
                        "clouds",
                    ],
                    name=None,
                )
            ],
        )

        # File extension
        file_ext = FileExtension.ext(asset, add_if_missing=True)
        file_ext.values = [
            MappingObject.create(values=[0], summary="No Data"),
            MappingObject.create(values=[1], summary="Water"),
            MappingObject.create(values=[2], summary="Trees"),
            MappingObject.create(values=[3], summary="Grass"),
            MappingObject.create(values=[4], summary="Flooded vegetation"),
            MappingObject.create(values=[5], summary="Crops"),
            MappingObject.create(values=[6], summary="Scrub/shrub"),
            MappingObject.create(values=[7], summary="Built area"),
            MappingObject.create(values=[8], summary="Bare ground"),
            MappingObject.create(values=[9], summary="Snow/ice"),
            MappingObject.create(values=[10], summary="Clouds"),
        ]


class NineClassIOCollection(BaseIOCollection):
    collection = IO_LULC_9_CLASS

    @classmethod
    def apply_classmap(cls, item: pystac.Item, asset: pystac.Asset) -> None:

        # File extension
        file_ext = FileExtension.ext(asset, add_if_missing=True)
        file_ext.values = [
            MappingObject.create(values=[0], summary="No Data"),
            MappingObject.create(values=[1], summary="Water"),
            MappingObject.create(values=[2], summary="Trees"),
            MappingObject.create(values=[4], summary="Flooded vegetation"),
            MappingObject.create(values=[5], summary="Crops"),
            MappingObject.create(values=[7], summary="Built area"),
            MappingObject.create(values=[8], summary="Bare ground"),
            MappingObject.create(values=[9], summary="Snow/ice"),
            MappingObject.create(values=[10], summary="Clouds"),
            MappingObject.create(values=[11], summary="Rangeland"),
        ]


class NineClassV2IOCollection(NineClassIOCollection):
    collection = IO_LULC_ANNUAL_V02
