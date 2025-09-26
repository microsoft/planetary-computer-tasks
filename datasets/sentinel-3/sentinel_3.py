import logging
import os
from hashlib import md5
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import List, Union

import pystac
import requests
import urllib3
from stactools.sentinel3.stac import create_item

import pctasks.dataset.collection
from pctasks.core.models.task import WaitTaskResult
from pctasks.core.storage import StorageFactory
from pctasks.core.utils.backoff import is_common_throttle_exception, with_backoff

handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("[%(levelname)s]:%(asctime)s: %(message)s"))
handler.setLevel(logging.INFO)
logger = logging.getLogger(__name__)
logger.addHandler(handler)
logger.setLevel(logging.INFO)


def browse_jpg_asset(jpg_path: str) -> pystac.Asset:
    # https://github.com/stactools-packages/sentinel3/issues/28
    # https://github.com/stactools-packages/sentinel3/issues/24
    return pystac.Asset(
        href=jpg_path,
        media_type=pystac.MediaType.JPEG,
        description="temp",
        roles=["thumbnail"],
        extra_fields={
            "file:size": os.path.getsize(jpg_path),
            "file:checksum": md5(open(jpg_path, "rb").read()).hexdigest(),
        },
    )


def eop_metadata_asset(eop_metadata_path: str) -> pystac.Asset:
    # https://github.com/stactools-packages/sentinel3/issues/28
    # https://github.com/stactools-packages/sentinel3/issues/24
    manifest_text = open(eop_metadata_path, encoding="utf-8").read()
    manifest_text_encoded = manifest_text.encode(encoding="UTF-8")
    return pystac.Asset(
        href=eop_metadata_path,
        media_type=pystac.MediaType.XML,
        description="temp",
        roles=["metadata"],
        extra_fields={
            "file:size": os.path.getsize(eop_metadata_path),
            "file:checksum": md5(manifest_text_encoded).hexdigest(),
        },
    )


def olci_lfr_fixups(item: pystac.Item, temp_sen3_dir: str) -> pystac.Item:
    asset_descriptions = {
        "safe-manifest": "SAFE product manifest",
        "gifapar": "Green instantaneous Fraction of Absorbed Photosynthetically Active Radiation (FAPAR)",  # noqa
        "ogvi": "OLCI Global Vegetation Index (OGVI)",
        "otci": "OLCI Terrestrial Chlorophyll Index (OTCI)",
        "iwv": "Integrated water vapour column",
        "rc-ogvi": "Rectified reflectance",
        "rc-gifapar": "Rectified reflectance",
        "lqsf": "Land quality and science flags",
        "time-coordinates": "Time coordinate annotations",
        "geo-coordinates": "Geo coordinate annotations",
        "tie-geo-coordinates": "Tie-point geo coordinate annotations",
        "tie-geometries": "Tie-point geometry annotations",
        "tie-meteo": "Tie-point meteo annotations",
        "instrument-data": "Instrument annotations",
    }
    for asset_key, asset in item.assets.items():
        if asset_key in asset_descriptions:
            asset.description = asset_descriptions[asset_key]
    return item


def olci_wfr_fixups(item: pystac.Item, temp_sen3_dir: str) -> pystac.Item:
    browse_jpg_path = os.path.join(temp_sen3_dir, "browse.jpg")
    if os.path.isfile(browse_jpg_path):
        item.assets["browse-jpg"] = browse_jpg_asset(browse_jpg_path)

    eop_metadata_path = os.path.join(temp_sen3_dir, "EOPMetadata.xml")
    if os.path.isfile(eop_metadata_path):
        item.assets["eop-metadata"] = eop_metadata_asset(eop_metadata_path)

    asset_descriptions = {
        "chl-nn": "Neural net chlorophyll concentration",
        "chl-oc4me": "OC4Me algorithm chlorophyll concentration",
        "iop-nn": "Inherent optical properties of water",
        "iwv": "Integrated water vapour column",
        "par": "Photosynthetically active radiation",
        "w-aer": "Aerosol over water",
        "geo-coordinates": "Geo coordinate annotations",
        "instrument-data": "Instrument annotations",
        "tie-geo-coordinates": "Tie-point geo coordinate annotations",
        "tie-geometries": "Tie-point geometry annotations",
        "tie-meteo": "Tie-point meteo annotations",
        "time-coordinates": "Time coordinate annotations",
        "wqsf": "Water quality and science flags",
        "eop-metadata": "Metadata produced by the European Organisation for the Exploitation of Meteorological Satellites (EUMETSAT)",  # noqa: E501
        "browse-jpg": "Preview image produced by the European Organisation for the Exploitation of Meteorological Satellites (EUMETSAT)",  # noqa: E501
    }
    for asset_key, asset in item.assets.items():
        if asset_key in asset_descriptions:
            asset.description = asset_descriptions[asset_key]

    return item


def slstr_lst_fixups(item: pystac.Item, temp_sen3_dir: str) -> pystac.Item:
    asset_descriptions = {
        "safe-manifest": "SAFE product manifest",
        "lst-in": "Land Surface Temperature (LST) values",
        "st-ancillary-ds": "LST ancillary measurement dataset",
        "slstr-flags-in": "Global flags for the 1km TIR grid, nadir view",
        "slstr-indices-in": "Scan, pixel and detector indices annotations for the 1km TIR grid, nadir view",  # noqa: E501
        "slstr-time-in": "Time annotations for the 1km grid",
        "slstr-geodetic-in": "Full resolution geodetic coordinates for the 1km TIR grid, nadir view",
        "slstr-cartesian-in": "Full resolution cartesian coordinates for the 1km TIR grid, nadir view",
        "slstr-geometry-tn": "16km solar and satellite geometry annotations, nadir view",
        "slstr-geodetic-tx": "16km geodetic coordinates",
        "slstr-cartesian-tx": "16km cartesian coordinates",
        "slstr-met-tx": "Meteorological parameters regridded onto the 16km tie points",
    }
    for asset_key, asset in item.assets.items():
        if asset_key in asset_descriptions:
            asset.description = asset_descriptions[asset_key]
    return item


def slstr_wst_fixups(item: pystac.Item, temp_sen3_dir: str) -> pystac.Item:
    browse_jpg_path = os.path.join(temp_sen3_dir, "browse.jpg")
    if os.path.isfile(browse_jpg_path):
        item.assets["browse-jpg"] = browse_jpg_asset(browse_jpg_path)

    eop_metadata_path = os.path.join(temp_sen3_dir, "EOPMetadata.xml")
    if os.path.isfile(eop_metadata_path):
        item.assets["eop-metadata"] = eop_metadata_asset(eop_metadata_path)

    asset_descriptions = {
        "safe-manifest": "SAFE product manifest",
        "l2p": "Skin Sea Surface Temperature (SST) values",
        "eop-metadata": "Metadata produced by the European Organisation for the Exploitation of Meteorological Satellites (EUMETSAT)",  # noqa: E501
        "browse-jpg": "Preview image produced by the European Organisation for the Exploitation of Meteorological Satellites (EUMETSAT)",  # noqa: E501
    }
    for asset_key, asset in item.assets.items():
        if asset_key in asset_descriptions:
            asset.description = asset_descriptions[asset_key]
    return item


def sral_lan_fixups(item: pystac.Item, temp_sen3_dir: str) -> pystac.Item:
    asset_descriptions = {
        "safe-manifest": "SAFE product manifest",
        "standard-measurement": "Standard measurement data file",
        "enhanced-measurement": "Enhanced measurement data file",
        "reduced-measurement": "Reduced measurement data file",
    }
    for asset_key, asset in item.assets.items():
        if asset_key in asset_descriptions:
            asset.description = asset_descriptions[asset_key]

        # https://github.com/stactools-packages/sentinel3/issues/25
        asset.extra_fields.pop("shape", None)
        asset.extra_fields.pop("s3:shape", None)

    return item


def sral_wat_fixups(item: pystac.Item, temp_sen3_dir: str) -> pystac.Item:
    eop_metadata_path = os.path.join(temp_sen3_dir, "EOPMetadata.xml")
    if os.path.isfile(eop_metadata_path):
        item.assets["eop-metadata"] = eop_metadata_asset(eop_metadata_path)

    asset_descriptions = {
        "safe-manifest": "SAFE product manifest",
        "standard-measurement": "Standard measurement data file",
        "enhanced-measurement": "Enhanced measurement data file",
        "reduced-measurement": "Reduced measurement data file",
        "eop-metadata": "Product metadata file produced by the European Organisation for the Exploitation of Meteorological Satellites (EUMETSAT)",  # noqa
    }
    for asset_key, asset in item.assets.items():
        if asset_key in asset_descriptions:
            asset.description = asset_descriptions[asset_key]

        # https://github.com/stactools-packages/sentinel3/issues/25
        asset.extra_fields.pop("shape", None)
        asset.extra_fields.pop("s3:shape", None)

    return item


def synergy_vgp_fixups(item: pystac.Item, temp_sen3_dir: str) -> pystac.Item:
    asset_descriptions = {
        "safe-manifest": "SAFE product manifest",
        "b0": "Top of atmosphere reflectance data set associated with the VGT-B0 channel",
        "b2": "Top of atmosphere reflectance data set associated with the VGT-B2 channel",
        "b3": "Top of atmosphere reflectance data set associated with the VGT-B3 channel",
        "mir": "Top of atmosphere Reflectance data set associated with the VGT-MIR channel",
        "vaa": "View azimuth angle data",
        "vza": "View zenith angle data",
        "saa": "Solar azimuth angle data",
        "sza": "Solar zenith angle data",
        "ag": "Aerosol optical thickness data",
        "og": "Total ozone column data",
        "wvg": "Total column water vapour data",
        "sm": "Status map data",
    }
    for asset_key, asset in item.assets.items():
        if asset_key in asset_descriptions:
            asset.description = asset_descriptions[asset_key]
    return item


FIXUP_FUNCS = {
    "olci-lfr": olci_lfr_fixups,
    "olci-wfr": olci_wfr_fixups,
    "slstr-lst": slstr_lst_fixups,
    "slstr-wst": slstr_wst_fixups,
    "sral-lan": sral_lan_fixups,
    "sral-wat": sral_wat_fixups,
    "synergy-vgp": synergy_vgp_fixups,
}


def backoff_throttle_check(e: Exception) -> bool:
    return (
        is_common_throttle_exception(e)
        or isinstance(e, urllib3.exceptions.ReadTimeoutError)
        or isinstance(e, requests.exceptions.ConnectionError)
    )


class Sentinel3Collections(pctasks.dataset.collection.Collection):
    @classmethod
    def create_item(
        cls, asset_uri: str, storage_factory: StorageFactory
    ) -> Union[List[pystac.Item], WaitTaskResult]:
        # Only create Items for NT (Not Time critical) products
        sen3_archive = os.path.dirname(asset_uri)
        assert sen3_archive.endswith(".SEN3")
        timeliness = sen3_archive[-11:-9]
        assert timeliness in ["NR", "ST", "NT"]
        if sen3_archive[-11:-9] != "NT":
            return []

        sen3_storage = storage_factory.get_storage(sen3_archive)

        with TemporaryDirectory() as temp_dir:
            temp_sen3_dir = Path(temp_dir, Path(sen3_archive).name)
            temp_sen3_dir.mkdir()
            for path in sen3_storage.list_files():
                with_backoff(
                    lambda: sen3_storage.download_file(
                        path, str(Path(temp_sen3_dir, path))
                    ),
                    is_throttle=backoff_throttle_check,
                )

            try:
                item: pystac.Item = create_item(str(temp_sen3_dir))
            except FileNotFoundError:
                # occasionally there is an empty file, e.g., a 0-byte netcdf
                logger.exception(
                    f"Missing file when attempting to create item for {asset_uri}"
                )
                return []

            fixup_function = FIXUP_FUNCS.get(item.properties["s3:product_name"], None)
            if fixup_function is not None:
                item = fixup_function(item, str(temp_sen3_dir))

            for asset in item.assets.values():
                path = Path(asset.href).name
                asset.href = sen3_storage.get_url(path)

        return [item]
