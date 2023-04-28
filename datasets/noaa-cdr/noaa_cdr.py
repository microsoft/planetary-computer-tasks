import logging
import os.path
import socket
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, List, Union

import stactools.noaa_cdr.constants
import stactools.noaa_cdr.ocean_heat_content.stac
import stactools.noaa_cdr.sea_ice_concentration.stac
import stactools.noaa_cdr.sea_surface_temperature_optimum_interpolation.stac
import stactools.noaa_cdr.sea_surface_temperature_whoi.stac
import stactools.noaa_cdr.stac
from pystac import Item, Link, MediaType

from pctasks.core.models.task import WaitTaskResult
from pctasks.core.storage import Storage, StorageFactory
from pctasks.dataset.collection import Collection

logger = logging.getLogger(__name__)

# Experiencing a rare hang in `_ssl` when downloading from Blob Storage.
# Unsure if this will help.
socket.setdefaulttimeout(600)


def cog_uri(name: str) -> str:
    return f"blob://noaacdr/cogs/{name}"


def get_download_kwargs(storage) -> dict[str, Any]:
    kwargs = {}
    if isinstance(storage, Storage):
        # timeout_seconds is a server-side timeout
        kwargs["timeout_seconds"] = 120
        # these two are client-side timeouts (eventually passed to urllib3)
        kwargs["connection_timeout"] = 240
        kwargs["read_timeout"] = 120
    return kwargs


class OceanHeatContentCollection(Collection):
    @classmethod
    def create_item(
        cls, asset_uri: str, storage_factory: StorageFactory
    ) -> Union[List[Item], WaitTaskResult]:
        directory = "/".join(asset_uri.split("/")[:-1])
        asset_storage = storage_factory.get_storage(directory)
        files = list(asset_storage.list_files(extensions=[".nc"]))
        cog_storage = storage_factory.get_storage(cog_uri("ocean-heat-content"))
        cog_files = cog_storage.list_files(extensions=[".tif"])
        cog_hrefs = [cog_storage.get_url(file) for file in cog_files]

        with TemporaryDirectory() as temporary_directory:
            local_netcdf_paths = []
            for file in files:
                path = os.path.join(temporary_directory, os.path.basename(file))
                asset_storage.download_file(
                    file, path, **get_download_kwargs(asset_storage)
                )
                local_netcdf_paths.append(path)
            items = stactools.noaa_cdr.ocean_heat_content.stac.create_items(
                hrefs=local_netcdf_paths,
                directory=temporary_directory,
                cog_hrefs=cog_hrefs,
            )
            for item in items:
                for key, asset in item.assets.items():
                    if asset.href.startswith(
                        temporary_directory
                    ) and asset.href.endswith(".tif"):
                        file_name = os.path.basename(asset.href)
                        cog_url = cog_storage.get_url(file_name)
                        cog_storage.upload_file(asset.href, file_name)
                        asset.href = cog_url
                        item.assets[key] = asset
                for file in files:
                    id = Path(file).with_suffix("").stem
                    parts = id.split("_")
                    max_depth = int(parts[-2].split("-")[-1])
                    interval = parts[-1]
                    # We use startswith rather than equals for interval because
                    # the filenames have "pentad" instead of "pendtadal"
                    if item.properties[
                        "noaa_cdr:max_depth"
                    ] == max_depth and item.properties["noaa_cdr:interval"].startswith(
                        interval
                    ):
                        item.add_link(
                            Link(
                                rel="derived-from",
                                target=f"collections/noaa-cdr-ocean-heat-content-netcdf/items/{id}",
                                media_type=MediaType.GEOJSON,
                                title="Source NetCDF item",
                            )
                        )
        return items


class OceanHeatContentNetcdfCollection(Collection):
    @classmethod
    def create_item(
        cls, asset_uri: str, storage_factory: StorageFactory
    ) -> Union[List[Item], WaitTaskResult]:
        asset_storage, asset_path = storage_factory.get_storage_for_file(asset_uri)
        with TemporaryDirectory() as temporary_directory:
            path = os.path.join(temporary_directory, os.path.basename(asset_path))
            asset_storage.download_file(
                asset_path, path, **get_download_kwargs(asset_storage)
            )
            item = stactools.noaa_cdr.ocean_heat_content.stac.create_netcdf_item(path)
            item.assets[
                stactools.noaa_cdr.constants.NETCDF_ASSET_KEY
            ].href = asset_storage.get_url(asset_path)
            return [item]


class SeaIceConcentrationCollection(Collection):
    """
    As of 2023-03-31, noaa-cdr-sea-ice-concentration does not work. The data in
    Azure blob storage is V2, but the data on the NOAA FTP site is V4, and the
    stactools package was developed against V4. We're retaining this section for
    the future when the Azure blob storage data is brought up-to-date.
    """

    @classmethod
    def create_item(
        cls, asset_uri: str, storage_factory: StorageFactory
    ) -> Union[List[Item], WaitTaskResult]:
        asset_storage, asset_path = storage_factory.get_storage_for_file(asset_uri)
        year = asset_path.split("/")[1]
        cog_storage = storage_factory.get_storage(cog_uri("sea-ice-concentration"))
        with TemporaryDirectory() as temporary_directory:
            file_name = os.path.basename(asset_path)
            outfile = os.path.join(temporary_directory, file_name)
            asset_storage.download_file(
                asset_path, outfile, **get_download_kwargs(asset_storage)
            )
            item = stactools.noaa_cdr.sea_ice_concentration.stac.create_item(outfile)
            item.assets[
                stactools.noaa_cdr.constants.NETCDF_ASSET_KEY
            ].href = asset_storage.get_url(asset_path)

            item = stactools.noaa_cdr.sea_ice_concentration.stac.add_cogs(
                item, temporary_directory
            )
            for key, asset in item.assets.items():
                if asset.media_type == MediaType.COG:
                    cog_path = f"{year}/{os.path.basename(asset.href)}"
                    cog_storage.upload_file(asset.href, cog_path)
                    asset.href = cog_storage.get_url(cog_path)
                    item.assets[key] = asset
        return [item]


class SeaSurfaceTemperatureOptimumInterpolationCollection(Collection):
    @classmethod
    def create_item(
        cls, asset_uri: str, storage_factory: StorageFactory
    ) -> Union[List[Item], WaitTaskResult]:
        asset_storage, asset_path = storage_factory.get_storage_for_file(asset_uri)
        if os.path.splitext(asset_path)[0].endswith("_preliminary"):
            return []
        prefix = asset_path.split("/")[-2]
        cog_storage = storage_factory.get_storage(
            cog_uri("sea-surface-temperature-optimum-interpolation")
        )
        with TemporaryDirectory() as temporary_directory:
            file_name = os.path.basename(asset_path)
            outfile = os.path.join(temporary_directory, file_name)
            asset_storage.download_file(
                asset_path, outfile, **get_download_kwargs(asset_storage)
            )
            item = stactools.noaa_cdr.sea_surface_temperature_optimum_interpolation.stac.create_item(  # noqa
                outfile
            )
            item.assets[
                stactools.noaa_cdr.constants.NETCDF_ASSET_KEY
            ].href = asset_storage.get_url(asset_path)

            item = stactools.noaa_cdr.stac.add_cogs(item, temporary_directory)
            for key, asset in item.assets.items():
                if asset.media_type == MediaType.COG:
                    cog_path = f"{prefix}/{os.path.basename(asset.href)}"
                    cog_storage.upload_file(asset.href, cog_path)
                    asset.href = cog_storage.get_url(cog_path)
                    item.assets[key] = asset
        return [item]


class SeaSurfaceTemperatureWhoiCollection(Collection):
    @classmethod
    def create_item(
        cls, asset_uri: str, storage_factory: StorageFactory
    ) -> Union[List[Item], WaitTaskResult]:
        asset_storage, asset_path = storage_factory.get_storage_for_file(asset_uri)
        year = asset_path.split("/")[1]
        cog_storage = storage_factory.get_storage(
            cog_uri("sea-surface-temperature-whoi")
        )
        with TemporaryDirectory() as temporary_directory:
            file_name = os.path.basename(asset_path)
            outfile = os.path.join(temporary_directory, file_name)
            asset_storage.download_file(
                asset_path, outfile, **get_download_kwargs(asset_storage)
            )
            items = (
                stactools.noaa_cdr.sea_surface_temperature_whoi.stac.create_cog_items(
                    outfile, temporary_directory
                )
            )
            for item in items:
                for key, asset in item.assets.items():
                    if asset.media_type == MediaType.COG:
                        cog_path = f"{year}/{os.path.basename(asset.href)}"
                        cog_storage.upload_file(asset.href, cog_path)
                        asset.href = cog_storage.get_url(cog_path)
                        item.assets[key] = asset
        return items


class SeaSurfaceTemperatureWhoiNetcdfCollection(Collection):
    @classmethod
    def create_item(
        cls, asset_uri: str, storage_factory: StorageFactory
    ) -> Union[List[Item], WaitTaskResult]:
        asset_storage, asset_path = storage_factory.get_storage_for_file(asset_uri)
        with TemporaryDirectory() as temporary_directory:
            file_name = os.path.basename(asset_path)
            outfile = os.path.join(temporary_directory, file_name)
            asset_storage.download_file(
                asset_path, outfile, **get_download_kwargs(asset_storage)
            )
            item = stactools.noaa_cdr.stac.create_item(outfile)
            item.assets[
                stactools.noaa_cdr.constants.NETCDF_ASSET_KEY
            ].href = asset_storage.get_url(asset_path)
        return [item]
