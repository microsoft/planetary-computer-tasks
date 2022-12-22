import logging
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import List
from zipfile import ZipFile

import planetary_computer
from pystac import Item, Link, MediaType
from stactools.usda_cdl import stac, tile
from stactools.usda_cdl.metadata import Metadata

from pctasks.core.models.base import PCBaseModel
from pctasks.core.storage import StorageFactory
from pctasks.dataset.collection import Collection
from pctasks.task.context import TaskContext
from pctasks.task.task import Task

handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("[%(levelname)s]:%(asctime)s: %(message)s"))
handler.setLevel(logging.INFO)
logger = logging.getLogger(__name__)
logger.addHandler(handler)
logger.setLevel(logging.INFO)


class TileInput(PCBaseModel):
    src_uri: str
    dst_uri: str


class TileOutput(PCBaseModel):
    pass


class TileTask(Task[TileInput, TileOutput]):
    _input_model = TileInput
    _output_model = TileOutput

    def run(self, input: TileInput, context: TaskContext) -> TileOutput:
        logger.info(f"tiling geotiffs in {input.src_uri}")
        zipfile_storage, zipfile_name = context.storage_factory.get_storage_for_file(
            input.src_uri
        )
        tile_storage = context.storage_factory.get_storage(input.dst_uri)
        existing_tiles = list()
        for file in tile_storage.list_files():
            path = Path(file)
            if path.suffix == ".tif":
                existing_tiles.append(path.name)
        with TemporaryDirectory() as temporary_directory:
            local_zipfile_path = Path(temporary_directory) / Path(zipfile_name).name
            zipfile_storage.download_file(zipfile_name, str(local_zipfile_path))
            with ZipFile(local_zipfile_path, "r") as zipfile:
                zipfile.extractall(temporary_directory)
            geotiff_paths = list(Path(temporary_directory).glob("*.tif"))
            tiles = Path(temporary_directory) / "tiles"
            for geotiff_path in geotiff_paths:
                logging.info(f"tiling {geotiff_path.name}")
                tiles.mkdir()
                paths = tile.tile_geotiff(
                    geotiff_path, tiles, existing_tiles=existing_tiles
                )
                logger.info(f"Uploading {len(paths)} tiles...")
                for path in paths:
                    metadata = Metadata.from_href(path)
                    x_min = metadata.tile.split("_")[0]
                    tile_storage.upload_file(
                        str(path), f"{x_min}/{path.name}", overwrite=True
                    )
                shutil.rmtree(tiles)
            logger.info(f"Done!")
        return TileOutput()


tile_task = TileTask()


class UsdaCdlCollection(Collection):
    @classmethod
    def create_item(cls, asset_uri: str, storage_factory: StorageFactory) -> List[Item]:
        tile_storage = storage_factory.get_storage(asset_uri)
        paths = tile_storage.list_files(extensions=[".tif"])
        urls = [tile_storage.get_url(path) for path in paths]
        items = stac.create_items_from_tiles(
            urls, read_href_modifier=planetary_computer.sign
        )
        updated_items = list()
        for item in items:
            item_type = item.extra_fields["usda_cdl:type"]
            if item_type == "cropland":
                year = item.common_metadata.start_datetime.year
                link = Link(
                    rel="source",
                    target=(
                        "https://landcoverdata.blob.core.windows.net/usda-cdl-onboarding/"
                        f"{year}_30m_cdls.zip"
                    ),
                    media_type="application/zip",
                    title=f"{year} National CDL",
                )
            elif item_type == "cultivated":
                year = item.common_metadata.start_datetime.year
                link = Link(
                    rel="source",
                    target=(
                        "https://landcoverdata.blob.core.windows.net/usda-cdl-onboarding/"
                        f"{year}_Cultivated_Layer.zip"
                    ),
                    media_type="application/zip",
                    title=f"{year} National Cultivated Layer",
                )
            elif item_type == "frequency":
                start_year = item.common_metadata.start_datetime.year
                end_year = item.common_metadata.end_datetime.year
                link = Link(
                    rel="source",
                    target=(
                        "https://landcoverdata.blob.core.windows.net/usda-cdl-onboarding/"
                        f"Crop_Frequency_{start_year}-{end_year}.zip"
                    ),
                    media_type="application/zip",
                    title=f"{end_year} National Frequency Layer",
                )
            item.add_link(link)
            updated_items.append(item)
        return updated_items
