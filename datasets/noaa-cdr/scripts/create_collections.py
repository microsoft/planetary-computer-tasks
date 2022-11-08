from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

import orjson
from pystac import Asset, Collection, MediaType, Provider, ProviderRole
from stactools.noaa_cdr.constants import NETCDF_ASSET_KEY

RAW_EXAMPLES_URL = (
    "https://raw.githubusercontent.com/stactools-packages/noaa-cdr/main/examples"
)
COLLECTIONS = Path(__file__).parents[1] / "collections"
SHORT_DESCRIPTION = {
    "ocean-heat-content": "The Ocean Heat Content Climate Data Record (CDR) is a set of ocean heat content anomaly (OHCA) time-series for 1955-present on 3-monthly, yearly, and pentadal (five-yearly) scales.",
    "sea-ice-concentration": "The Sea Ice Concentration Climate Data Record (CDR) provides a consistent daily and monthly time series of sea ice concentrations for both the north and south Polar Regions on a 25 km x 25 km grid.",
    "sea-surface-temperature-optimum-interpolation": "The NOAA 1/4° daily Optimum Interpolation Sea Surface Temperature (or daily OISST) Climate Data Record (CDR) provides complete ocean temperature fields constructed by combining bias-adjusted observations from different platforms (satellites, ships, buoys) on a regular global grid, with gaps filled in by interpolation.",
    "sea-surface-temperature-whoi": "The Sea Surface Temperature-Woods Hole Oceanographic Institution (WHOI) Climate Data Record (CDR) is one of three CDRs which combine to form the NOAA Ocean Surface Bundle (OSB) CDR. The resultant sea surface temperature (SST) data are produced through modeling the diurnal variability in combination with AVHRR SST observations.",
}


@dataclass
class CollectionFileContent:
    template: Dict[str, Any]
    description: str

    @classmethod
    def from_name(cls, name: str) -> "CollectionFileContent":
        url = f"{RAW_EXAMPLES_URL}/noaa-cdr-{name}/collection.json"
        collection = Collection.from_file(url)
        description = collection.description
        collection.description = "{{ collection.description }}"
        collection.clear_items()
        assert collection.providers
        noaa = collection.providers[0]
        noaa.roles = [
            ProviderRole.PRODUCER,
            ProviderRole.PROCESSOR,
            ProviderRole.LICENSOR,
        ]
        microsoft = Provider(
            name="Microsoft",
            roles=[ProviderRole.PROCESSOR, ProviderRole.HOST],
            url="https://planetarycomputer.microsoft.com",
        )
        collection.providers = [noaa, microsoft]
        collection.extra_fields["msft:short_description"] = SHORT_DESCRIPTION[name]
        collection.extra_fields["msft:storage_account"] = "noaacdr"
        collection.extra_fields["msft:container"] = name
        collection.extra_fields["msft:group_id"] = "noaa-cdr"
        collection.extra_fields["msft:region"] = "eastus"

        collection.assets = {}
        collection.add_asset(
            "thumbnail",
            Asset(
                f"https://ai4edatasetspublicassets.blob.core.windows.net/assets/pc_thumbnails/noaa-cdr-{name}-thumb.png",
                title=f"{collection.title} thumbnail",
                media_type=MediaType.PNG,
                roles=["thumbnail"],
            ),
        )
        collection.add_asset(
            "geoparquet-items",
            Asset(
                f"abfs://items/noaa-cdr-{name}.parquet",
                title="GeoParquet STAC items",
                description=(
                    "Snapshot of the collection's STAC items "
                    "exported to GeoParquet format"
                ),
                media_type="application/x-parquet",
                roles=["stac-items"],
                extra_fields={
                    "msft:partition_info": {"is_partitioned": False},
                    "table:storage_options": {"account_name": "pcstacitems"},
                },
            ),
        )

        collection_as_dict = collection.to_dict(include_self_link=False)
        collection_as_dict["links"] = [
            l for l in collection_as_dict["links"] if l["rel"] not in {"root", "parent"}
        ]  # Required until https://github.com/stac-utils/pystac/pull/896
        return CollectionFileContent(
            template=collection_as_dict, description=description
        )

    def write(self, name: str) -> None:
        directory = COLLECTIONS / name
        directory.mkdir(exist_ok=True)
        with open(directory / "template.json", "w") as f:
            f.write(
                orjson.dumps(self.template, option=orjson.OPT_INDENT_2).decode("utf-8")
            )
        with open(directory / "description.md", "w") as f:
            f.write(self.description)


def create_collection(name: str) -> None:
    collection_file_content = CollectionFileContent.from_name(name)
    collection_file_content.write(name)


def create_netcdf_collection(name: str) -> None:
    collection_file_content = CollectionFileContent.from_name(name)
    collection = collection_file_content.template
    collection_file_content.description += f"\n\nThis is a NetCDF-only collection, for Cloud-Optimized GeoTIFFS use collection '{collection['id']}'."
    collection["id"] += "-netcdf"
    collection["item_assets"] = {
        NETCDF_ASSET_KEY: {
            "type": "application/netcdf",
            "roles": ["data"],
        }
    }
    collection["title"] += " NetCDFs"
    del collection["assets"]["thumbnail"]
    collection["assets"]["geoparquet-items"][
        "href"
    ] = f"abfs://items/noaa-cdr-{name}-netcdf.parquet"
    collection_file_content.write(f"{name}-netcdf")


create_collection("ocean-heat-content")
create_netcdf_collection("ocean-heat-content")
create_collection("sea-ice-concentration")
create_collection("sea-surface-temperature-optimum-interpolation")
create_collection("sea-surface-temperature-whoi")
create_netcdf_collection("sea-surface-temperature-whoi")
