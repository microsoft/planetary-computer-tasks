import logging
from typing import Union

from pctasks.core.models.task import WaitTaskResult
from pctasks.core.storage import StorageFactory
from pctasks.dataset.collection import Collection
from pystac import Item
from stactools.met_office_deterministic import stac
from stactools.met_office_deterministic.constants import Model, Theme

handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("[%(levelname)s]:%(asctime)s: %(message)s"))
handler.setLevel(logging.INFO)
logger = logging.getLogger(__name__)
logger.addHandler(handler)
logger.setLevel(logging.INFO)


class MetOfficeCollection(Collection):
    model: Model
    theme: Theme

    @classmethod
    def create_item(
        cls, asset_uri: str, storage_factory: StorageFactory
    ) -> Union[list[Item], WaitTaskResult]:
        logger.info(f"Creating items for {asset_uri}")
        storage = storage_factory.get_storage(asset_uri)
        hrefs = list(storage.get_url(path) for path in storage.list_files())
        logger.info(f"Found {len(hrefs)} hrefs")
        items = stac.create_items(hrefs, model=cls.model, theme=cls.theme)
        return items


class MetOfficeGlobalHeightCollection(MetOfficeCollection):
    model = Model.global_
    theme = Theme.height


class MetOfficeGlobalNearSurfaceCollection(MetOfficeCollection):
    model = Model.global_
    theme = Theme.near_surface


class MetOfficeGlobalPressureCollection(MetOfficeCollection):
    model = Model.global_
    theme = Theme.pressure_level


class MetOfficeGlobalWholeAtmosphereCollection(MetOfficeCollection):
    model = Model.global_
    theme = Theme.whole_atmosphere


class MetOfficeUkHeightCollection(MetOfficeCollection):
    model = Model.uk
    theme = Theme.height


class MetOfficeUkNearSurfaceCollection(MetOfficeCollection):
    model = Model.uk
    theme = Theme.near_surface


class MetOfficeUkPressureCollection(MetOfficeCollection):
    model = Model.uk
    theme = Theme.pressure_level


class MetOfficeUkWholeAtmosphereCollection(MetOfficeCollection):
    model = Model.uk
    theme = Theme.whole_atmosphere
