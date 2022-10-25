import logging
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import List, Union

import pystac
from stactools.noaa_climate_normals.tabular.stac import (
    create_item as tabular_create_item,
)
from stactools.noaa_climate_normals.tabular.constants import Period as TabularPeriod
from stactools.noaa_climate_normals.tabular.constants import (
    Frequency as TabularFrequency,
)

from pctasks.core.models.task import WaitTaskResult
from pctasks.core.storage import StorageFactory
from pctasks.dataset.collection import Collection

GEOPARQUET_CONTAINER = "blob://noaanormals/climate-normals-geoparquet"


class MissingGeoParquet(Exception):
    pass


class NoaaClimateNormalsTabular(Collection):
    @classmethod
    def create_item(
        cls, asset_uri: str, storage_factory: StorageFactory
    ) -> Union[List[pystac.Item], WaitTaskResult]:

        csv_directory = Path(asset_uri).parent
        period = TabularPeriod[csv_directory.parts[-2]]
        frequency = TabularFrequency[csv_directory.parts[-3]]

        csv_storage = storage_factory.get_storage(csv_directory)
        csv_paths = list(csv_storage.list_files(extensions=[".csv"]))
        csv_urls = [csv_storage.get_url(csv_path) for csv_path in csv_paths]

        with TemporaryDirectory() as tmp_dir:
            # create item and geoparquet
            item = tabular_create_item(
                csv_hrefs=csv_urls,
                frequency=frequency,
                period=period,
                parquet_dir=tmp_dir,
                read_href_modifier=csv_storage.sign,
            )

            geoparquet_filename = f"{period.value.replace('-', '_')}-{frequency}.parquet"
            geoparquet_path = Path(tmp_dir, geoparquet_filename)
            if not geoparquet_path.exists():
                raise MissingGeoParquet(
                    f"Expected '{geoparquet_filename}' to be created, but not found."
                )

            # upload geoparquet file to Azure container and update href
            geoparquet_storage = storage_factory.get_storage(GEOPARQUET_CONTAINER)
            geoparquet_storage.upload_file(geoparquet_path, geoparquet_filename)
            item.assets["parquet"].href = geoparquet_storage.get_url(geoparquet_filename)

        return [item]


class NoaaClimateNormalsNetcdf(Collection):
    def create_item(
        cls, asset_uri: str, storage_factory: StorageFactory
    ) -> Union[List[pystac.Item], WaitTaskResult]:
        pass
