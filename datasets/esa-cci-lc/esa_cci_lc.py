from tempfile import TemporaryDirectory
from typing import List, Union
from pathlib import Path

import pystac
from stactools.esa_cci_lc.cog.stac import create_items as cog_create_items
from stactools.esa_cci_lc.netcdf.stac import create_item as netcdf_create_item

from pctasks.core.models.task import WaitTaskResult
from pctasks.core.storage import StorageFactory
from pctasks.dataset.collection import Collection


class EsaCciLcCog(Collection):
    @classmethod
    def create_item(
        cls, asset_uri: str, storage_factory: StorageFactory
    ) -> Union[List[pystac.Item], WaitTaskResult]:

        with TemporaryDirectory() as tmp_dir:
            storage, nc_path = storage_factory.get_storage_for_file(asset_uri)
            tmp_nc_path = str(Path(tmp_dir, Path(nc_path).name))
            storage.download_file(nc_path, tmp_nc_path)

            items = cog_create_items(nc_path=tmp_nc_path, cog_dir=tmp_dir)

            for item in items:
                id_parts = item.id.split("-")
                *_, year, version, tile = id_parts
                # update cog asset hrefs and upload to storage
                for asset in item.assets.values():
                    asset_path = str(
                        Path(nc_path).parent.parent
                        / "cog"
                        / version
                        / tile
                        / year
                        / Path(asset.href).name
                    )
                    storage.upload_file(asset.href, asset_path)
                    asset.href = storage.get_url(asset_path)
                # add link to source netcdf stac item
                item.links.append(
                    pystac.Link(
                        rel=pystac.RelType.DERIVED_FROM,
                        title="Source NetCDF Item",
                        media_type=pystac.MediaType.JSON,
                        target=(
                            f"collections/esa-cci-lc-netcdf/items/"
                            f"{'-'.join(id_parts[:-1])}"
                        ),
                    )
                )

        return items


class EsaCciLcNetcdf(Collection):
    @classmethod
    def create_item(
        cls, asset_uri: str, storage_factory: StorageFactory
    ) -> Union[List[pystac.Item], WaitTaskResult]:

        with TemporaryDirectory() as tmp_dir:
            storage, nc_path = storage_factory.get_storage_for_file(asset_uri)
            tmp_nc_path = str(Path(tmp_dir, Path(nc_path).name))
            storage.download_file(nc_path, tmp_nc_path)

            item = netcdf_create_item(tmp_nc_path)
            item.assets["netcdf"].href = storage.get_url(nc_path)

        return [item]
