from __future__ import annotations

import datetime
import re
from dataclasses import dataclass
from typing import List, Union

import stactools.noaa_hrrr.stac
from pctasks.dataset.collection import Collection
from pystac import Item
from stactools.noaa_hrrr import CloudProvider, Product, Region


class NoaaHrrrCollection(Collection):
    @classmethod
    def create_item(
        cls, asset_uri: str, storage_factory: ..., **kwargs: ...
    ) -> Union[List[Item], Item]:
        parsed_uri = NoaaHrrrUri.parse(asset_uri)
        item = stactools.noaa_hrrr.stac.create_item(
            parsed_uri.region,
            parsed_uri.product,
            CloudProvider.azure,
            parsed_uri.reference_datetime,
            parsed_uri.forecast_hour,
        )
        return item


@dataclass
class NoaaHrrrUri:
    region: Region
    product: Product
    reference_datetime: datetime.datetime
    forecast_hour: int

    _PATTERN = re.compile(
        r"hrrr\.(\d{4})(\d{2})(\d{2})"
        r"/(?P<region>conus|alaska)"
        r"/hrrr\.t(?P<cc>\d{2})z"
        r"\.wrf(?P<product>prs|nat|sfc|subh)f(?P<fh>\d+)\.grib2$"
    )

    _PRODUCTS = {
        "prs": Product.prs,
        "nat": Product.nat,
        "sfc": Product.sfc,
        "subh": Product.subh,
    }

    @classmethod
    def parse(cls, s: str) -> NoaaHrrrUri:
        match = cls._PATTERN.search(s)
        if not match:
            raise ValueError(f"Could not parse HRRR URI: {s}")

        year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))
        cc = int(match.group("cc"))
        reference_datetime = datetime.datetime(
            year, month, day, cc, tzinfo=datetime.timezone.utc
        )

        return cls(
            region=Region(match.group("region")),
            product=cls._PRODUCTS[match.group("product")],
            reference_datetime=reference_datetime,
            forecast_hour=int(match.group("fh")),
        )
