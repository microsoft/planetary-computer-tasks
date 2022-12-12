import logging
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import List, Union

import pystac
import requests
from stactools.noaa_climate_normals.gridded.constants import (
    Frequency as GriddedFrequency,
)
from stactools.noaa_climate_normals.gridded.constants import Period as GriddedPeriod
from stactools.noaa_climate_normals.gridded.stac import (
    create_items as gridded_create_items,
)
from stactools.noaa_climate_normals.gridded.utils import nc_href_dict
from stactools.noaa_climate_normals.netcdf.stac import create_item as netcdf_create_item
from stactools.noaa_climate_normals.tabular.constants import (
    Frequency as TabularFrequency,
)
from stactools.noaa_climate_normals.tabular.constants import Period as TabularPeriod
from stactools.noaa_climate_normals.tabular.stac import (
    create_item as tabular_create_item,
)

from pctasks.core.models.task import WaitTaskResult
from pctasks.core.storage import StorageFactory
from pctasks.dataset.collection import Collection
from pctasks.core.storage.base import Storage

PARQUET_CONTAINER = "blob://noaanormals/climate-normals-geoparquet"
COG_CONTAINER = "blob://noaanormals/gridded-normals-cogs"
NETCDF_STAC_API_URL = "https://planetarycomputer.microsoft.com/api/stac/v1/collections/noaa-climate-normals-netcdf/items/"  # noqa

handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("[%(levelname)s]:%(asctime)s: %(message)s"))
handler.setLevel(logging.INFO)
logger = logging.getLogger(__name__)
logger.addHandler(handler)
logger.setLevel(logging.INFO)


class MissingGeoParquet(Exception):
    pass


class NoaaClimateNormalsTabular(Collection):
    @classmethod
    def create_item(
        cls, asset_uri: str, storage_factory: StorageFactory
    ) -> Union[List[pystac.Item], WaitTaskResult]:

        uri_parts = asset_uri.split("/")
        period = TabularPeriod(uri_parts[-3])
        frequency = TabularFrequency(uri_parts[-4].split("-")[-1])

        csv_storage = storage_factory.get_storage("/".join(uri_parts[:-1]))
        csv_paths = list(csv_storage.list_files(extensions=[".csv"]))

        parquet_storage = storage_factory.get_storage(PARQUET_CONTAINER)
        parquet_directory = f"{period.value.replace('-', '_')}-{frequency}.parquet"

        logger.info(
            f"Processing Climate Normals for Period '{period}', Frequency '{frequency}'"
        )

        with TemporaryDirectory() as tmp_dir:
            # download CSVs
            tmp_csv_paths = []
            for csv_path in csv_paths:
                tmp_csv_paths.append(Path(tmp_dir, csv_path))
                csv_storage.download_file(csv_path, tmp_csv_paths[-1], timeout_seconds=10)

            # create Item
            logger.info("Creating Item and GeoParquet")
            item = tabular_create_item(
                csv_hrefs=tmp_csv_paths,
                frequency=frequency,
                period=period,
                geoparquet_dir=tmp_dir,
                num_partitions=5,
            )

            # upload created GeoParquet to Azure and update Item asset href
            logger.info("Uploading GeoParquet")
            parquet_path = Path(tmp_dir, parquet_directory)
            if not parquet_path.exists():
                raise MissingGeoParquet(
                    f"Expected '{parquet_directory}' to be created, but not found."
                )
            parquet_file_paths = parquet_path.glob("*.parquet")
            for parquet_file_path in parquet_file_paths:
                parquet_storage.upload_file(
                    parquet_file_path, f"{parquet_directory}/{parquet_file_path.name}"
                )

            item.assets["geoparquet"].href = parquet_storage.fsspec_path(
                parquet_directory
            )
            item.assets["geoparquet"].extra_fields["table:storage_options"] = {
                "account_name": "noaanormals"
            }

        return [item]


class NoaaClimateNormalsNetcdf(Collection):
    @classmethod
    def create_item(
        cls, asset_uri: str, storage_factory: StorageFactory
    ) -> Union[List[pystac.Item], WaitTaskResult]:

        asset_storage, asset_path = storage_factory.get_storage_for_file(asset_uri)
        item = netcdf_create_item(asset_storage.get_url(asset_path))

        return [item]


class NoaaClimateNormalsGridded(Collection):
    @classmethod
    def create_item(
        cls, asset_uri: str, storage_factory: StorageFactory
    ) -> Union[List[pystac.Item], WaitTaskResult]:

        path_parts = Path(asset_uri).name.split("-")
        frequency = GriddedFrequency(path_parts[-3])
        period = GriddedPeriod(path_parts[-4].replace("_", "-"))

        with TemporaryDirectory() as tmp_dir:
            tmp_nc_dir = Path(tmp_dir, "nc")
            tmp_cog_dir = Path(tmp_dir, "cog")
            Path.mkdir(tmp_nc_dir)
            Path.mkdir(tmp_cog_dir)

            # download the netcdfs to avoid repeated remote data calls
            all_nc_uris = nc_href_dict(asset_uri, frequency)
            for nc_uri in all_nc_uris.values():
                nc_storage, nc_path = storage_factory.get_storage_for_file(nc_uri)
                tmp_nc_path = Path(tmp_nc_dir, Path(nc_path).name)
                nc_storage.download_file(nc_path, tmp_nc_path)

            # create all items
            all_items = gridded_create_items(
                nc_href=tmp_nc_path,
                cog_dir=tmp_cog_dir,
                api_url_netcdf=NETCDF_STAC_API_URL
            )

            # upload created COGs to Azure and update Item asset hrefs
            def get_cog_storage(_frequency: str) -> Storage:
                return storage_factory.get_storage(
                    f"{COG_CONTAINER}/normals-{_frequency}/{period}/"
                )
            cog_storage_dict = {}
            if frequency is GriddedFrequency.DAILY:
                cog_storage_dict["daily"] = get_cog_storage("daily")
            else:
                cog_storage_dict["monthly"] = get_cog_storage("monthly")
                cog_storage_dict["seasonal"] = get_cog_storage("seasonal")
                cog_storage_dict["annual"] = get_cog_storage("annual")

            for item in all_items:
                for asset_key, asset_value in item.assets.items():
                    cog_filename = f"{item.id}-{asset_key}.tif"
                    _frequency = item.id.split("-")[1]
                    cog_storage = cog_storage_dict[_frequency]
                    cog_storage.upload_file(
                        Path(tmp_cog_dir, cog_filename), cog_filename
                    )
                    asset_value.href = cog_storage.get_url(cog_filename)

        return all_items
