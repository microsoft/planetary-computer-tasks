from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Iterable, List, Union

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

GEOPARQUET_CONTAINER = "blob://noaanormals/climate-normals-geoparquet"
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

            geoparquet_filename = (
                f"{period.value.replace('-', '_')}-{frequency}.parquet"
            )
            geoparquet_path = Path(tmp_dir, geoparquet_filename)
            if not geoparquet_path.exists():
                raise MissingGeoParquet(
                    f"Expected '{geoparquet_filename}' to be created, but not found."
                )

            # upload geoparquet file to Azure container and update href
            geoparquet_storage = storage_factory.get_storage(GEOPARQUET_CONTAINER)
            geoparquet_storage.upload_file(geoparquet_path, geoparquet_filename)
            item.assets["geoparquet"].href = geoparquet_storage.get_url(
                geoparquet_filename
            )

            # add table:storage_options to asset
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

        def process_items_cogs(
            _nc_href: str,
            _frequency: GriddedFrequency,
            _cog_dir: str,
            _time_indices: Iterable[int],
            _storage_factory: StorageFactory,
            _period: GriddedPeriod,
            _path_fragment: str
        ) -> List[pystac.Item]:
            # create items and cogs
            _items: List[pystac.Item] = []
            for index in _time_indices:
                _items.append(
                    gridded_create_item(
                        nc_href=_nc_href,
                        frequency=_frequency,
                        cog_dir=_cog_dir,
                        api_url_netcdf=NETCDF_STAC_API_URL,
                        time_index=index,
                    )
                )
            # upload cogs to Azure, update cog asset hrefs
            cog_storage = _storage_factory.get_storage(
                f"{COG_CONTAINER}/normals-{_path_fragment}/{_period}/"
            )
            for _item in _items:
                id_parts = _item.id.split("-")
                index_for_name = id_parts[-1] if index is not None else None
                base = "-".join(id_parts[:2])
                for key, value in _item.assets.items():
                    cog_filename = f"{base}-{key}.tif"
                    if index_for_name:
                        cog_filename = f"{cog_filename[:-4]}-{index_for_name}.tif"
                    cog_storage.upload_file(
                        Path(_cog_dir, cog_filename), cog_filename
                    )
                    value.href = cog_storage.get_url(cog_filename)
            return _items

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

            # create items and cogs
            items: List[pystac.Item] = []
            if frequency is GriddedFrequency.DAILY:
                indices = range(1, 367)
                num_cogs = 6 * 366
                path_fragment = "daily"
                items.extend(
                    process_items_cogs(
                        _nc_href=tmp_nc_path,
                        _frequency=frequency,
                        _cog_dir=tmp_cog_dir,
                        _time_indices=indices,
                        _storage_factory=storage_factory,
                        _period=period,
                        _path_fragment=path_fragment
                    )
                )
            elif frequency is GriddedFrequency.MLY:
                # monthly files contain monthly, seasonal, and annual data
                num_cogs = 4 * 20 + 12 * 20 + 1 * 20
                contained = {
                    "monthly": {
                        "frequency": GriddedFrequency.MLY,
                        "indices": range(1, 13),
                    },
                    "seasonal": {
                        "frequency": GriddedFrequency.SEAS,
                        "indices": range(1, 5)
                    },
                    "annual": {
                        "frequency": GriddedFrequency.ANN,
                        "indices": [None]
                    }
                }
                for key, value in contained.items():
                    items.extend(
                        process_items_cogs(
                            _nc_href=tmp_nc_path,
                            _frequency=value["frequency"],
                            _cog_dir=tmp_cog_dir,
                            _time_indices=value["indices"],
                            _storage_factory=storage_factory,
                            _period=period,
                            _path_fragment=key
                        )
                    )
            else:
                raise ValueError(f"Unexpected frequency: {frequency.name}")

            local_cogs = list(tmp_cog_dir.glob("*.tif"))
            if len(local_cogs) != num_cogs:
                raise ValueError(
                    f"Incorrect number of COGs produced: "
                    f"{num_cogs} expected, but {len(local_cogs)} produced."
                )

        return items
