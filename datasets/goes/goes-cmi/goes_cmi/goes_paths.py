from typing import Dict, Optional, Tuple

from stactools.goes.enums import PlatformId, ProductAcronym
from stactools.goes.file_name import ABIL2FileName
from stactools.goes.product import PRODUCTS

from pctasks.core.storage.base import Storage


class MissingGOESDataError(Exception):
    pass


class DuplicateGOESDataError(Exception):
    pass


class GOESPaths:
    """Defines the layout of GOES-R data assets stored in
    Azure as part of the Microsoft Planetary Computer

    Args:
        nc_href: HREF to a single NetCDF asset. This will define all other paths.
    """

    def __init__(self, nc_path: str, asset_storage: Storage) -> None:
        self.asset_storage = asset_storage
        self.reference_nc_path = nc_path
        self.reference_file_name = ABIL2FileName.from_href(nc_path)

        # First folder is product folder, so don't consider that
        # Also chop off file name.
        self.folder = "/".join(nc_path.split("/")[1:-1])

        self.nc_paths: Dict[Tuple[ProductAcronym, Optional[int]], str] = {
            (
                self.reference_file_name.product,
                self.reference_file_name.channel,
            ): nc_path
        }

    def _get_product_folder(self, product: ProductAcronym) -> str:
        return f"ABI-L2-{product.value}{self.reference_file_name.image_type.value}"

    def get_nc_path(
        self, product: ProductAcronym, channel: Optional[int] = None
    ) -> str:
        if (product, channel) not in self.nc_paths:
            parts = [self._get_product_folder(product)]

            parts.append(self.folder)

            if channel:
                parts.append(
                    self.reference_file_name.get_channel_file_prefix(product, channel)
                )
            else:
                parts.append(self.reference_file_name.get_product_file_prefix(product))

            prefix = "/".join(parts)

            blobs = list(self.asset_storage.list_files(name_starts_with=prefix))
            if len(blobs) == 0:
                raise MissingGOESDataError(
                    f"No netCDF file found for product {product.value} "
                    f"based on {self.reference_nc_path} "
                    f"(prefix {prefix})"
                )
            elif len(blobs) > 1:
                # It's rare, but we can have multiple files with the same prefix
                # They'll typically have different "end" times, which come after the
                # prefix. In the cases we've identified (n=1) the smaller file was
                # all NaN, so we find the larger file.
                sizes = [self.asset_storage.get_file_info(blob) for blob in blobs]
                idx = max(enumerate(sizes), key=lambda x: x[1].size)[0]
                blob = blobs[idx]
            else:
                blob = blobs[0]

            self.nc_paths[(product, channel)] = blob

        return self.nc_paths[(product, channel)]

    def get_cog_paths(
        self, product: ProductAcronym, channel: Optional[int] = None
    ) -> Dict[str, str]:
        nc_path = self.get_nc_path(product, channel=channel)
        nc_file_name = ABIL2FileName.from_href(nc_path)
        cog_file_names = PRODUCTS[product].get_cog_file_names(nc_file_name)

        path_parts = []
        if nc_file_name.platform == PlatformId.G17:
            path_parts.append("goes-17")
        elif nc_file_name.platform == PlatformId.G18:
            path_parts.append("goes-18")
        else:
            path_parts.append("goes-16")
        path_parts.append(self._get_product_folder(product))
        path_parts.append(self.folder)

        return {
            var: "/".join(path_parts + [cog_file_name])
            for var, cog_file_name in cog_file_names.items()
        }
