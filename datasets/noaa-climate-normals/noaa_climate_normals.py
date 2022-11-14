from pathlib import Path
from tempfile import TemporaryDirectory
from typing import List, Union

import pystac
from stactools.noaa_climate_normals.gridded.constants import (
    Frequency as GriddedFrequency,
)
from stactools.noaa_climate_normals.gridded.constants import Period as GriddedPeriod
from stactools.noaa_climate_normals.gridded.stac import (
    create_item as gridded_create_item,
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

PARQUET_CONTAINER = "blob://noaanormals/climate-normals-geoparquet"
COG_CONTAINER = "blob://noaanormals/gridded-normals-cogs"
NETCDF_STAC_API_URL = "https://planetarycomputer.microsoft.com/api/stac/v1/collections/noaa-climate-normals-netcdf/items/"  # noqa


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
        parquet_filename = f"{period.value.replace('-', '_')}-{frequency}.parquet"

        with TemporaryDirectory() as tmp_dir:
            tmp_csv_paths = []
            for csv_path in csv_paths:
                tmp_csv_paths.append(Path(tmp_dir, csv_path))
                csv_storage.download_file(csv_path, tmp_csv_paths[-1])

            item = tabular_create_item(
                csv_hrefs=tmp_csv_paths,
                frequency=frequency,
                period=period,
                geoparquet_dir=tmp_dir,
            )

            parquet_path = Path(tmp_dir, parquet_filename)
            if not parquet_path.exists():
                raise MissingGeoParquet(
                    f"Expected '{parquet_filename}' to be created, but not found."
                )
            parquet_storage.upload_file(parquet_path, parquet_filename)

            item.assets["geoparquet"].href = parquet_storage.get_url(parquet_filename)
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

            # download the netcdfs
            all_nc_uris = nc_href_dict(asset_uri, frequency)
            for nc_uri in all_nc_uris.values():
                nc_storage, nc_path = storage_factory.get_storage_for_file(nc_uri)
                tmp_nc_path = Path(tmp_nc_dir, Path(nc_path).name)
                nc_storage.download_file(nc_path, tmp_nc_path)

            # prep for item and cog creation
            if frequency is GriddedFrequency.DAILY:
                num_cogs = 6 * 366
                data = {
                    "daily": {
                        "frequency": GriddedFrequency.DAILY,
                        "indices": range(1, 367),
                    }
                }
            elif frequency is GriddedFrequency.MLY:
                num_cogs = 4 * 20 + 12 * 20 + 1 * 20
                data = {
                    "monthly": {
                        "frequency": GriddedFrequency.MLY,
                        "indices": range(1, 13),
                    },
                    "seasonal": {
                        "frequency": GriddedFrequency.SEAS,
                        "indices": range(1, 5),
                    },
                    "annual": {"frequency": GriddedFrequency.ANN, "indices": [1]},
                }
            else:
                raise ValueError(f"Unexpected frequency: {frequency.name}")

            # create items and cogs
            all_items: List[pystac.Item] = []
            for key, value in data.items():
                items = []
                for index in value["indices"]:
                    items.append(
                        gridded_create_item(
                            nc_href=tmp_nc_path,
                            frequency=value["frequency"],
                            time_index=index,
                            cog_dir=tmp_cog_dir,
                            api_url_netcdf=NETCDF_STAC_API_URL,
                        )
                    )

                cog_storage = storage_factory.get_storage(
                    f"{COG_CONTAINER}/normals-{key}/{period}/"
                )

                for item in items:
                    for asset_key, asset_value in item.assets.items():
                        cog_filename = f"{item.id}-{asset_key}.tif"
                        cog_storage.upload_file(
                            Path(tmp_cog_dir, cog_filename), cog_filename
                        )
                        asset_value.href = cog_storage.get_url(cog_filename)

                all_items.extend(items)

            local_cogs = list(tmp_cog_dir.glob("*.tif"))
            if len(local_cogs) != num_cogs:
                raise ValueError(
                    f"Incorrect number of COGs produced: "
                    f"{num_cogs} expected, but {len(local_cogs)} produced."
                )

        return all_items
