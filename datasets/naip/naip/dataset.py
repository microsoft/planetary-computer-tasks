import logging
import re
from typing import List, Union

import pystac
from pctasks.core.models.task import WaitTaskResult
from pctasks.core.storage import StorageFactory
from pctasks.dataset.collection import Collection
from stactools.naip import stac

logger = logging.getLogger(__name__)

naip_regex = re.compile(
    r"v\d\d\d/(?P<state>[^/]+)/(?P<year>[^/]+)/"
    r"(?P<image_dir>[^/]+)/(?P<area>[^/]+)/(?P<fname>[^/]+).tif"
)


class Naip(Collection):
    @classmethod
    def create_item(
        cls, asset_uri: str, storage_factory: StorageFactory
    ) -> Union[List[pystac.Item], WaitTaskResult]:
        """Creates a STAC Item for NAIP.

        Args:
            asset_uri: URI to the NAIP GeoTIFF
            storage_factory: The storage cache used to access the asset.
        """
        asset_storage, path = storage_factory.get_storage_for_file(asset_uri)

        if not asset_storage.file_exists(path):
            raise Exception(f"{path} does not exist in {path}")

        m = re.match(naip_regex, path)
        if not m:
            raise Exception(f"{path} did not match regex")

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

        thumbnail_path = f"v002/{state}/{year}/{image_dir}" f"/{area}/{fname}.200.jpg"

        # Account for the fact that some images don't have FGDC metadata
        if not asset_storage.file_exists(fgdc_path):
            fgdc_exists = False
        else:
            fgdc_exists = True

        if not asset_storage.file_exists(thumbnail_path):
            raise Exception(f"{thumbnail_path} does not exist in {asset_storage}")

        fgdc_href = asset_storage.get_url(fgdc_path)
        cog_href = asset_storage.get_url(path)
        thumbnail_href = asset_storage.get_url(thumbnail_path)

        logger.info("Creating STAC Item for {}...".format(cog_href))
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

        return [item]
