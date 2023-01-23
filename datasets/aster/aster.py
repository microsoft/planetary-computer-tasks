import itertools
import logging
from typing import Any, Dict, List, Optional, Union

import geopandas
import numpy
import orjson
import planetary_computer
import rasterio
import stac_geoparquet
import stactools.aster
import stactools.aster.utils
from adlfs import AzureBlobFileSystem
from pystac import Collection, Item, ItemCollection
from pystac.extensions.eo import EOExtension
from pystac.extensions.projection import ProjectionExtension
from pystac.extensions.raster import RasterBand, RasterExtension
from stactools.aster.constants import NO_DATA

from pctasks.core.models.base import PCBaseModel
from pctasks.core.models.task import WaitTaskResult
from pctasks.core.storage import StorageFactory
from pctasks.dataset.collection import Collection as PcTasksCollection
from pctasks.task.context import TaskContext
from pctasks.task.task import Task

handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("[%(levelname)s]:%(asctime)s: %(message)s"))
handler.setLevel(logging.INFO)
logger = logging.getLogger(__name__)
logger.addHandler(handler)
logger.setLevel(logging.INFO)


class GetPartitionsInput(PCBaseModel):
    url: str
    asset_key: str


class GetPartitionsOutput(PCBaseModel):
    assets: List[Dict[str, Any]]


class GetPartitionsTask(Task[GetPartitionsInput, GetPartitionsOutput]):
    _input_model = GetPartitionsInput
    _output_model = GetPartitionsOutput

    def run(
        self, input: GetPartitionsInput, context: TaskContext
    ) -> GetPartitionsOutput:
        collection = Collection.from_file(input.url)
        asset = collection.assets[input.asset_key]
        base_path = "/".join(asset.href.split("/")[-2:])
        asset = planetary_computer.sign_asset(asset)
        filesystem = AzureBlobFileSystem(**asset.extra_fields["table:storage_options"])
        assets = list()
        for i, path in enumerate(filesystem.ls(base_path)):
            partition_asset = asset.clone()
            partition_asset.href = f"abfs://{path}"
            asset_as_dict = partition_asset.to_dict()
            asset_as_dict["partition_number"] = i
            assets.append(asset_as_dict)
        return GetPartitionsOutput(assets=assets)


get_partitions_task = GetPartitionsTask()


class CreateChunksInput(PCBaseModel):
    asset: Dict[str, Any]
    dst_uri: str
    chunk_size: int
    limit: Optional[int] = None


class Chunk(PCBaseModel):
    uri: str
    id: str
    partition_number: str


class CreateChunksOutput(PCBaseModel):
    chunks: List[Chunk]


class CreateChunksTask(Task[CreateChunksInput, CreateChunksOutput]):
    _input_model = CreateChunksInput
    _output_model = CreateChunksOutput

    def run(self, input: CreateChunksInput, context: TaskContext) -> CreateChunksOutput:
        asset = input.asset
        item_collection = read_item_collection(
            asset["href"], storage_options=asset["table:storage_options"]
        )
        chunks = []
        chunk = []
        for item in itertools.islice(item_collection, input.limit):
            chunk.append(fix_dict(item.to_dict(include_self_link=False)))
            if len(chunk) >= input.chunk_size:
                chunks.append(chunk)
                chunk = []
        if chunk:
            chunks.append(chunk)
        output = []
        for i, chunk in enumerate(chunks):
            uri = f"{input.dst_uri}/{asset['partition_number']}/{i}.ndjson"
            storage, path = context.storage_factory.get_storage_for_file(uri)
            storage.write_text(
                path, "\n".join(orjson.dumps(item).decode("utf-8") for item in chunk)
            )
            output.append(
                Chunk(
                    uri=storage.get_uri(path),
                    id=str(i),
                    partition_number=str(asset["partition_number"]),
                )
            )
        return CreateChunksOutput(chunks=output)


create_chunks_task = CreateChunksTask()


class UpdateItemsInput(PCBaseModel):
    partition_number: int
    chunk_uri: str
    chunk_id: int
    item_chunkset_uri: str
    simplify_tolerance: float


class UpdateItemsOutput(PCBaseModel):
    ndjson_uri: str


class UpdateItemsTask(Task[UpdateItemsInput, UpdateItemsOutput]):
    _input_model = UpdateItemsInput
    _output_model = UpdateItemsOutput

    def run(self, input: UpdateItemsInput, context: TaskContext) -> UpdateItemsOutput:
        storage, path = context.storage_factory.get_storage_for_file(input.chunk_uri)
        items_as_dicts = storage.read_ndjson(path)
        items = list()
        error_items = list()
        for item in (Item.from_dict(d) for d in items_as_dicts):
            try:
                new_item = sign_and_update(item, input.simplify_tolerance)
            except Exception as e:
                logger.error(e)
                error_items.append(fix_dict(item.to_dict(include_self_link=False)))
            else:
                items.append(fix_dict(new_item.to_dict(include_self_link=False)))
        logger.info(f"{len(items)} items updated, {len(error_items)} errors")
        storage, path = context.storage_factory.get_storage_for_file(
            f"{input.item_chunkset_uri}/{input.partition_number}/{input.chunk_id}.ndjson"
        )
        storage.write_text(
            path, "\n".join(orjson.dumps(item).decode("utf-8") for item in items)
        )
        error_storage, error_path = context.storage_factory.get_storage_for_file(
            f"{input.item_chunkset_uri}/{input.partition_number}/{input.chunk_id}-errors.ndjson"
        )
        error_storage.write_text(
            error_path,
            "\n".join(orjson.dumps(item).decode("utf-8") for item in error_items),
        )
        return UpdateItemsOutput(ndjson_uri=storage.get_uri(path))


update_items_task = UpdateItemsTask()


def sign_and_update(item: Item, simplify_tolerance: float) -> Item:
    updated_item = stactools.aster.utils.update_geometry(
        planetary_computer.sign(item),
        simplify_tolerance=simplify_tolerance,
    )
    item.geometry = updated_item.geometry
    item.bbox = updated_item.bbox
    item.clear_links("root")
    item.clear_links("parent")
    item.clear_links("collection")
    item.clear_links("preview")
    RasterExtension.add_to(item)
    for sensor in stactools.aster.constants.ASTER_SENSORS:
        if sensor in item.assets:
            asset = item.assets[sensor]
            eo = EOExtension.ext(asset)
            assert eo.bands
            projection = ProjectionExtension.ext(asset)
            assert projection.transform is not None
            bands = []
            with rasterio.open(asset.href) as dataset:
                for eo_band, dtype in zip(eo.bands, dataset.dtypes):
                    spatial_resolution = round(projection.transform[0])
                    band = RasterBand.create(
                        nodata=NO_DATA,
                        data_type=dtype,
                        spatial_resolution=spatial_resolution,
                    )
                    band.properties["name"] = eo_band.name
                    bands.append(band)
                raster = RasterExtension.ext(asset)
                raster.bands = bands
    return item


def fix_assets(assets: Dict[str, Any]) -> Dict[str, Any]:
    return {key: value for key, value in assets.items() if value}


def fix(value: Any) -> Any:
    if isinstance(value, numpy.ndarray):
        return fix_list(list(value))
    elif isinstance(value, List):
        return fix_list(value)
    elif isinstance(value, Dict):
        return fix_dict(value)
    elif isinstance(value, numpy.float64):
        return float(value)
    elif isinstance(value, numpy.int64):
        return int(value)
    else:
        return value


def fix_dict(d: Dict[str, Any]) -> Dict[str, Any]:
    return dict((key, fix(value)) for key, value in d.items())


def fix_list(l: List[Any]) -> List[Any]:
    return [fix(value) for value in l]


class AsterL1tCollection(PcTasksCollection):
    @classmethod
    def create_item(
        cls, asset_uri: str, storage_factory: StorageFactory
    ) -> Union[List[Item], WaitTaskResult]:
        raise NotImplementedError


def read_item_collection(
    href: str, storage_options: Optional[Any] = None
) -> ItemCollection:
    dataframe = geopandas.read_parquet(href, storage_options=storage_options)
    dataframe["assets"] = dataframe["assets"].apply(fix_assets)
    dataframe["stac_extensions"] = [
        extension.tolist() for extension in dataframe.stac_extensions
    ]
    return stac_geoparquet.stac_geoparquet.to_item_collection(dataframe)
