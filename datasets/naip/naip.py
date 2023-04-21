import os
import functools
from dataclasses import dataclass
import re
import logging
from typing import List, Union


import azure.storage.blob
import subprocess
import pystac
from pctasks.core.utils.backoff import with_backoff
from stactools.naip import stac

from pctasks.core.storage.blob import BlobStorage
from pctasks.core.models.task import WaitTaskResult
from pctasks.core.storage import StorageFactory
from pctasks.dataset.collection import Collection


logger = logging.getLogger("pctasks.naip")

naip_regex = re.compile(
    r"v002/(?P<state>[^/]+)/(?P<year>[^/]+)/"
    r"(?P<image_dir>[^/]+)/(?P<area>[^/]+)/(?P<fname>[^/]+).tif"
)


@dataclass
class YearMismatchErrorRecord:
    tif_path: str

    @classmethod
    def create(cls, path: str) -> "YearMismatchErrorRecord":
        return cls(
            record_id=f"DUPLICATE_WRONG_YEAR-{path}",
            reason="DUPLICATE_WRONG_YEAR",
            tif_path=path,
        )

    @staticmethod
    def is_wrong_year(path: str) -> bool:
        year_regex = (
            r"(?P<state>\w{2})/(?P<folder_year>\d{4})/\w{2}_100cm_(?P<file_year>\d{4})"
        )
        m = re.search(year_regex, path)
        if m:
            return m.group("folder_year") != m.group("file_year")
        else:
            return False


def create_thumbnail(cog_signed_href: str, thumbnail_name: str) -> str:
    subprocess.check_output(
        [
            "gdal_translate",
            "-outsize",
            "200",
            "0",
            "-b",
            "1",
            "-b",
            "2",
            "-b",
            "3",
            f"/vsicurl/{cog_signed_href}",
            thumbnail_name,
        ]
    )
    return thumbnail_name


class NAIPCollection(Collection):
    @classmethod
    def create_item(
        cls, asset_uri: str, storage_factory: StorageFactory
    ) -> Union[List[pystac.Item], WaitTaskResult]:
        cog_storage, cog_path = storage_factory.get_storage_for_file(asset_uri)

        if not cog_storage.file_exists(cog_path):
            raise Exception(f"{cog_path} does not exist in {cog_storage}")

        m = re.match(naip_regex, cog_path)
        if not m:
            raise Exception(f"{cog_path} did not match regex")

        if YearMismatchErrorRecord.is_wrong_year(cog_path):
            raise ValueError(f"Mismatched year for asset at path {cog_path}")

        state = m.group("state")
        year = m.group("year")
        image_dir = m.group("image_dir")
        area = m.group("area")
        fname = m.group("fname")

        # Remove any processing numbers from the fname
        # for FGDC
        fgdc_fname = "_".join(fname.split("_")[:6])

        fgdc_path = (
            f"v002/{state}/{year}/{state}_fgdc_{year}" f"/{area}/{fgdc_fname}.txt"
        )

        thumbnail_name = f"{fname}.200.jpg"
        thumbnail_path = f"v002/{state}/{year}/{image_dir}" f"/{area}/{thumbnail_name}"

        # Account for the fact that some images don't have FGDC metadata
        if not cog_storage.file_exists(fgdc_path):
            fgdc_exists = False
        else:
            fgdc_exists = True

        fgdc_href = cog_storage.get_url(fgdc_path)
        cog_href = cog_storage.get_url(cog_path)

        if not cog_storage.file_exists(thumbnail_path):
            logger.debug("Creating thumbnail %s", thumbnail_path)
            thumbnail_f = functools.partial(create_thumbnail, cog_href, thumbnail_name)
            with_backoff(thumbnail_f, is_throttle=lambda x: True)
            kwargs = {}
            if isinstance(cog_storage, BlobStorage):
                kwargs["content_settings"] = azure.storage.blob.ContentSettings(
                    content_type="image/jpeg"
                )

            cog_storage.upload_file(thumbnail_name, thumbnail_path, **kwargs)

        assert cog_storage.file_exists(thumbnail_path)

        thumbnail_href = cog_storage.get_url(thumbnail_path)

        logger.debug("Creating STAC Item for {}...".format(cog_href))
        try:
            item = stac.create_item(
                state=state,
                year=year,
                fgdc_metadata_href=fgdc_href if fgdc_exists else None,
                cog_href=cog_href,
                thumbnail_href=thumbnail_href,
            )
        except UnicodeDecodeError:
            # Try once more, but without fgdc
            item = stac.create_item(
                state=state,
                year=year,
                fgdc_metadata_href=None,
                cog_href=cog_href,
                thumbnail_href=thumbnail_href,
            )

        # Compatibility with older STAC items.
        item.properties.pop("grid:code", None)
        item.assets["image"].extra_fields.pop("raster:bands", None)
        item.stac_extensions = [
            "https://stac-extensions.github.io/eo/v1.0.0/schema.json",
            "https://stac-extensions.github.io/projection/v1.0.0/schema.json",
        ]

        return [item]
