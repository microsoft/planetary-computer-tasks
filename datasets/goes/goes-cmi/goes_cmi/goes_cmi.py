import asyncio.exceptions
import logging
import os
from concurrent import futures
from concurrent.futures.process import BrokenProcessPool
from copy import deepcopy
from tempfile import TemporaryDirectory
from typing import Any, Callable, Dict, List, Optional, Tuple, TypeVar, Union

import pystac
import rasterio.errors
from goes_cmi.goes_errors import CogifyError, ErrorRecord, MissingExtent, OpenFileError
from goes_cmi.goes_paths import GOESPaths, MissingGOESDataError
from h5py import File
from pystac.extensions.projection import ProjectionExtension
from stactools.goes import CogifyError as StactoolsCogifyError
from stactools.goes import cog, stac
from stactools.goes.enums import ProductAcronym
from stactools.goes.errors import GOESInvalidGeometryError, GOESMissingExtentError
from stactools.goes.file_name import ABIL2FileName
from stactools.goes.product import PRODUCTS

from pctasks.core.models.task import WaitTaskResult
from pctasks.core.storage import StorageFactory
from pctasks.core.storage.base import Storage
from pctasks.core.utils.backoff import (
    BackoffStrategy,
    is_common_throttle_exception,
    with_backoff,
)
from pctasks.dataset.collection import Collection

handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("[%(levelname)s]:%(asctime)s: %(message)s"))
handler.setLevel(logging.INFO)
logger = logging.getLogger(__name__)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

T = TypeVar("T")

GOES_COG_STORAGE_ACCOUNT = "goeseuwest"
GOES_COG_CONTAINER = "noaa-goes-cogs"
GOES_COG_STORAGE_URL = f"blob://{GOES_COG_STORAGE_ACCOUNT}/{GOES_COG_CONTAINER}"

WEB_COG_FOLDER_PREFIX = "web"
WEB_COG_SUFFIX = "wm"


def should_generate_web_cog(product: ProductAcronym, variable: str) -> bool:
    # If it's MCMIP, generate for bands 1, 2 and 3
    if product == ProductAcronym.MCMIP:
        return variable in ["CMI_C01", "CMI_C02", "CMI_C03"]

    # Don't generate any for CMIP
    if product == ProductAcronym.CMIP:
        return False

    # Otherwise, generate for all that aren't the data quality flags
    return variable != "DQF"


def test_no_hdf_file_segfault(path: str) -> None:
    with open(path, "rb") as f:
        with File(f) as dataset:
            [key for key in dataset.keys()]


class SegfaultTestFailError(Exception):
    pass


class GoesCmiCollection(Collection):
    _segfault_test_pool: Optional[futures.ProcessPoolExecutor] = None
    _segfault_test_pool_shutdown: bool = False

    @classmethod
    def backoff_throttle_check(cls, e: Exception) -> bool:
        """Used in cls.with_backoff to check if exceptions
        should be considered throttle exceptions.

        Returns True if exception is a throttle exception.
        """
        return (
            is_common_throttle_exception(e)
            or isinstance(e, rasterio.errors.RasterioIOError)
            or isinstance(e, asyncio.exceptions.TimeoutError)
        )

    @classmethod
    def with_backoff(cls, fn: Callable[[], T]) -> T:
        return with_backoff(
            fn,
            is_throttle=cls.backoff_throttle_check,
            strategy=BackoffStrategy(),
        )

    @classmethod
    def _get_segfault_test_pool(cls) -> futures.ProcessPoolExecutor:
        if cls._segfault_test_pool is None or cls._segfault_test_pool_shutdown:
            cls._segfault_test_pool = futures.ProcessPoolExecutor(max_workers=1)
            cls._segfault_test_pool_shutdown = False
        return cls._segfault_test_pool

    @classmethod
    def ensure_no_segfault(cls, f: Callable[..., Any], *args: Any) -> None:
        pool = cls._get_segfault_test_pool()
        try:
            proc = pool.submit(f, *args)
            proc.result()
        except BrokenProcessPool as e:
            logger.error(e)
            raise SegfaultTestFailError() from e

    @classmethod
    def _download_cog(cls, href: str, cog_storage: Storage, local_cog_dir: str) -> str:
        cog_path = cog_storage.get_path_from_url(href)
        logger.info(f"Downloading {cog_path}...")
        local_path = os.path.join(local_cog_dir, os.path.basename(cog_path))
        cls.with_backoff(lambda: cog_storage.download_file(cog_path, local_path))
        return local_path

    @classmethod
    def download_create_and_upload_cogs(
        cls,
        asset_storage: Storage,
        cog_storage: Storage,
        item_id: str,
        nc_path: str,
        local_cog_dir: str,
        cog_hrefs: Dict[str, str],
        web_cog_hrefs: Dict[str, str],
        cogs_to_create: List[str],
        web_cogs_to_create: List[str],
    ) -> Union[Dict[str, str], ErrorRecord]:
        """Returns mapping of cog HREF to local copy"""
        created_cogs: Dict[str, str] = {}
        created_web_cogs: Dict[str, str] = {}

        if cogs_to_create or web_cogs_to_create:
            # Create COGs

            with TemporaryDirectory() as nc_tmp_dir:
                download_result = cls._download_and_test_nc(
                    asset_storage=asset_storage, nc_path=nc_path, tmp_dir=nc_tmp_dir
                )

                if isinstance(download_result, OpenFileError):
                    return download_result

                local_nc_path = download_result

                try:
                    if cogs_to_create:
                        created_cogs = cog.cogify(
                            local_nc_path,
                            local_cog_dir,
                            variables_to_include=cogs_to_create,
                        )

                    if web_cogs_to_create:
                        created_web_cogs = cog.cogify(
                            local_nc_path,
                            local_cog_dir,
                            variables_to_include=web_cogs_to_create,
                            target_srs="epsg:3857",
                            additional_suffix=WEB_COG_SUFFIX,
                        )

                    logger.info("...done stactools cogify calls.")
                except StactoolsCogifyError as e:
                    logger.error(e)
                    return CogifyError.create(item_id=item_id, path=nc_path)
                except GOESMissingExtentError as e:
                    logger.error(e)
                    return MissingExtent.create(path=nc_path)
                except KeyError as e:
                    logger.error(e)
                    return CogifyError.create(item_id=item_id, path=nc_path)

                # Upload

                for var, source in created_cogs.items():
                    destination = cog_storage.get_path_from_url(cog_hrefs[var])
                    logger.info(f"Uploading COG to {destination}...")
                    cog_storage.upload_file(source, destination)
                    logger.info("...done uploading COG")
                for var, source in created_web_cogs.items():
                    destination = cog_storage.get_path_from_url(web_cog_hrefs[var])
                    logger.info(f"Uploading COG to {destination}...")
                    cog_storage.upload_file(source, destination)
                    logger.info("...done uploading COG")

        # Download existing COGs

        cog_hrefs_to_local_copies: Dict[str, str] = {}

        for var, href in cog_hrefs.items():
            if var in cogs_to_create:
                cog_hrefs_to_local_copies[href] = created_cogs[var]
            else:
                cog_hrefs_to_local_copies[href] = cls._download_cog(
                    href, cog_storage, local_cog_dir
                )

        for var, href in web_cog_hrefs.items():
            if var in web_cogs_to_create:
                cog_hrefs_to_local_copies[href] = created_web_cogs[var]
            else:
                cog_hrefs_to_local_copies[href] = cls._download_cog(
                    href, cog_storage, local_cog_dir
                )

        return cog_hrefs_to_local_copies

    @classmethod
    def _download_and_test_nc(
        cls, asset_storage: Storage, nc_path: str, tmp_dir: str
    ) -> Union[str, OpenFileError]:
        """Downloads an netCDF file and tests that it doesn't segfault"""
        nc_url = asset_storage.get_url(nc_path)
        local_nc_path = os.path.join(tmp_dir, ABIL2FileName.from_href(nc_url).to_str())
        logger.info(f"  - Downloading file {nc_path}...")
        asset_storage.download_file(nc_path, local_nc_path)

        # Test that opening and closing works;
        # otherwise reading could segfault.

        logger.info("  - Testing that file doesn't segfault...")
        try:
            cls.ensure_no_segfault(test_no_hdf_file_segfault, local_nc_path)
        except SegfaultTestFailError as e:
            logger.error(e)
            return OpenFileError.create(path=nc_path, segfault=True)
        except Exception as e:
            logger.error(e)
            return OpenFileError.create(path=nc_path, segfault=False)
        logger.info(" - File opens!")
        return local_nc_path

    @classmethod
    def create_item(
        cls, asset_uri: str, storage_factory: StorageFactory
    ) -> Union[List[pystac.Item], WaitTaskResult]:
        file_name = ABIL2FileName.from_href(asset_uri)
        logger.info(f" ---- Processing {file_name}...")

        cog_storage = storage_factory.get_storage(GOES_COG_STORAGE_URL)
        asset_storage, asset_path = storage_factory.get_storage_for_file(asset_uri)

        with TemporaryDirectory() as tmp_dir:
            local_cog_dir = os.path.join(tmp_dir, "cog")
            os.makedirs(local_cog_dir)

            # Download and test the primary netCDF file

            download_result = cls._download_and_test_nc(
                asset_storage, asset_path, tmp_dir
            )
            if isinstance(download_result, OpenFileError):
                logger.error("Error downloading file %s", asset_path, exc_info=True)
                return []
            local_nc_path = download_result

            # Configure products to process

            products: List[Tuple[ProductAcronym, Optional[int]]] = [
                (file_name.product, None)
            ]
            if file_name.product == ProductAcronym.MCMIP:
                # Process MCMIP and CMIP together, keyed off
                # of MCMIP chunk lines.
                # Otherwise each product gets its own Item
                # Second item in tuple is the channel number (band)
                for band_idx in range(1, 17):
                    products.append((ProductAcronym.CMIP, band_idx))

            # Determine HREFS for Assets

            goes_paths = GOESPaths(asset_path, asset_storage)
            product_hrefs = []

            # Key is (product, channel, variable)
            web_cog_hrefs: Dict[Tuple[ProductAcronym, Optional[int], str], str] = {}

            # COG href to local copy
            local_cogs: Dict[str, str] = {}

            for product, channel in products:
                logger.info(f"  -= Processing {product.value} (channel: {channel}) =-")

                try:
                    product_nc_path = goes_paths.get_nc_path(product, channel)
                except MissingGOESDataError as e:
                    logger.exception(e)
                    logger.warning(
                        f" !!! MISSING {product.value} {channel} from {asset_uri}"
                    )
                    # Skip this product.
                    continue

                logger.info(f"  nc: {product_nc_path}")

                # Check if COGs exist; if not create.

                product_cog_hrefs: Dict[str, str] = {}
                product_web_cog_hrefs: Dict[str, str] = {}
                cogs_to_create: List[str] = []
                web_cogs_to_create: List[str] = []

                def get_web_cog_path(cog_path: str) -> str:
                    base, ext = os.path.splitext(cog_path)

                    return os.path.join(
                        WEB_COG_FOLDER_PREFIX, f"{base}_{WEB_COG_SUFFIX}{ext}"
                    )

                # Skip if it's CMIP we won't use COGs for
                if product != ProductAcronym.CMIP or channel in [1, 2, 3, 5]:
                    for variable, cog_path in goes_paths.get_cog_paths(
                        product, channel
                    ).items():
                        product_cog_hrefs[variable] = cog_storage.get_url(cog_path)

                        logger.info(f"Checking if COG {cog_path} exists...")
                        if not with_backoff(
                            lambda: cog_storage.file_exists(cog_path)  # type: ignore
                        ):
                            cogs_to_create.append(variable)

                        # Check web cogs, if we're making them.
                        if should_generate_web_cog(product, variable):
                            web_cog_path = get_web_cog_path(cog_path)

                            product_web_cog_hrefs[variable] = cog_storage.get_url(
                                web_cog_path
                            )

                            logger.info(f"Checking if Web COG {web_cog_path} exists...")
                            if not with_backoff(
                                lambda: cog_storage.file_exists(web_cog_path)  # type: ignore
                            ):
                                web_cogs_to_create.append(variable)

                    # Create and upload any missing COGs

                    logger.info("Processing COGs ...")
                    cog_result = cls.download_create_and_upload_cogs(
                        asset_storage=asset_storage,
                        cog_storage=cog_storage,
                        item_id=file_name.get_item_id(),
                        nc_path=product_nc_path,
                        local_cog_dir=local_cog_dir,
                        cog_hrefs=product_cog_hrefs,
                        web_cog_hrefs=product_web_cog_hrefs,
                        cogs_to_create=cogs_to_create,
                        web_cogs_to_create=web_cogs_to_create,
                    )

                    if isinstance(cog_result, ErrorRecord):
                        logger.warning(
                            f"Cannot get cogs for {product.value} "
                            f"{channel} from {asset_uri}"
                        )
                        logger.warning(f"Error is: {cog_result.reason}")
                        for variable in cogs_to_create:
                            product_cog_hrefs.pop(variable, None)

                        for variable in web_cogs_to_create:
                            web_cog_hrefs.pop((product, channel, variable), None)
                    else:
                        local_cogs = {**local_cogs, **cog_result}

                product_hrefs.append(
                    stac.ProductHrefs(
                        asset_storage.get_url(product_nc_path),
                        cog_hrefs=product_cog_hrefs or None,
                    )
                )

                for var in product_web_cog_hrefs:
                    web_cog_hrefs[(product, channel, var)] = product_web_cog_hrefs[var]

            # Create STAC Item

            nc_url = asset_storage.get_url(asset_path)

            def read_href_modifier(href: str) -> str:
                # Use local nc path we've already downloaded
                if href == nc_url:
                    return local_nc_path

                if href in local_cogs:
                    return local_cogs[href]

                # Otherwise sign based on the container
                if href.endswith(".nc"):
                    return asset_storage.sign(href)  # type: ignore
                else:
                    return cog_storage.sign(href)  # type: ignore

            logger.info("Creating Item from stactools...")

            try:
                item = with_backoff(
                    lambda: stac.create_item(  # type: ignore
                        product_hrefs,
                        read_href_modifier=read_href_modifier,
                        backoff_func=cls.with_backoff,
                    ),
                    strategy=BackoffStrategy(waits=[0.2, 0.5]),
                )
            except GOESInvalidGeometryError as e:
                logger.exception(e)
                logger.warning("Bad geometry!")
                return []
            except GOESMissingExtentError as e:
                logger.exception(e)
                logger.warning("Missing extent!")
                return []
            except KeyError as e:
                logger.exception(e)
                logger.warning("Missing key!")
                return []

            logger.info("...done creating item from stactools.")

            # Remove some asset prefixes for usability

            if file_name.product == ProductAcronym.MCMIP:
                remove_prefix = "CMI"
            else:
                remove_prefix = f"{file_name.product.value}"

            for asset_key, asset in list(item.assets.items()):
                if asset_key.startswith(f"{remove_prefix}_"):
                    new_key = asset_key.replace(f"{remove_prefix}_", "")
                    item.assets[new_key] = asset
                    item.assets.pop(asset_key)
                if asset_key == f"{remove_prefix}-nc":
                    new_key = "data"
                    item.assets[new_key] = asset
                    item.assets.pop(asset_key)

            # Add web cog assets

            logger.info("Adding Web COGS...")

            web_cog_map = []
            if file_name.product == ProductAcronym.MCMIP:
                web_cog_map = [
                    ("C01_2km", (ProductAcronym.MCMIP, None, "CMI_C01")),
                    ("C02_2km", (ProductAcronym.MCMIP, None, "CMI_C02")),
                    ("C03_2km", (ProductAcronym.MCMIP, None, "CMI_C03")),
                ]
            else:
                web_cog_map = [
                    (asset_key, (file_name.product, None, asset_key))
                    for (asset_key, asset) in item.assets.items()
                    if "data" in (asset.roles or [])
                    and asset.media_type == pystac.MediaType.COG
                ]

            for asset_key, web_cog_key in web_cog_map:
                logger.info(f"Checking {asset_key}...")
                web_cog_href = web_cog_hrefs.get(web_cog_key)

                if web_cog_href:
                    asset = item.assets.get(asset_key)
                    if asset:
                        web_asset = deepcopy(asset)
                        web_asset.href = web_cog_href
                        web_asset.title = f"{web_asset.title}, Web Mercator"
                        web_proj = ProjectionExtension.ext(web_asset)
                        web_proj.epsg = 3857
                        web_proj.wkt2 = None

                        def _read_raster_metadata() -> None:
                            local_cog_path = cls._download_cog(web_cog_href, cog_storage, local_cog_dir)  # type: ignore
                            with rasterio.open(local_cog_path) as ds:
                                web_proj.transform = list(ds.transform)[:6]
                                web_proj.shape = list(ds.shape)
                                web_proj.bbox = list(ds.bounds)

                        with_backoff(_read_raster_metadata)

                        web_cog_asset_key = f"{asset_key}_{WEB_COG_SUFFIX}"
                        logger.info(f"Adding web cog asset {web_cog_asset_key}")
                        item.assets[web_cog_asset_key] = web_asset
                    else:
                        logger.warning(f"Missing expected asset key {asset_key}")
                else:
                    logger.warning(f"Missing expected web cog {web_cog_key}")

            logger.info("...done adding Web COGs")

            return [item]
