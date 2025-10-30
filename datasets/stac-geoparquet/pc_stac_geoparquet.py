from __future__ import annotations

import argparse
import collections.abc
import dataclasses
import datetime
import hashlib
import itertools
import json
import logging
import os
import time
import urllib
from typing import Any, Set, Union

import azure.core.credentials
import azure.data.tables
import azure.identity

import dateutil
import fsspec
import pandas as pd
import pystac
import requests
from stac_geoparquet.arrow import to_parquet
from stac_geoparquet.pgstac_reader import (
    get_pgstac_partitions,
    Partition,
    pgstac_to_arrow,
    pgstac_to_iter,
)

from pctasks.core.models.base import PCBaseModel
from pctasks.core.models.task import FailedTaskResult, WaitTaskResult
from pctasks.task.context import TaskContext
from pctasks.task.task import Task
import tqdm.auto
import tempfile
from stac_geoparquet.arrow import (
    parse_stac_items_to_arrow,
)


handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("[%(levelname)s]:%(asctime)s: %(message)s"))
handler.setLevel(logging.DEBUG)
logger = logging.getLogger(__name__)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)

CHUNK_SIZE = 8192

PARTITION_FREQUENCIES = {
    "3dep-lidar-classification": "YS",
    "3dep-lidar-copc": "YS",
    "3dep-lidar-dsm": "YS",
    "3dep-lidar-dtm": "YS",
    "3dep-lidar-dtm-native": "YS",
    "3dep-lidar-hag": "YS",
    "3dep-lidar-intensity": "YS",
    "3dep-lidar-pointsourceid": "YS",
    "3dep-lidar-returns": "YS",
    "3dep-seamless": None,
    "alos-dem": None,
    "alos-fnf-mosaic": "YS",
    "alos-palsar-mosaic": "YS",
    "aster-l1t": "YS",
    "chloris-biomass": None,
    "cil-gdpcir-cc-by": None,
    "cil-gdpcir-cc-by-sa": None,
    "cil-gdpcir-cc0": None,
    "cop-dem-glo-30": None,
    "cop-dem-glo-90": None,
    "eclipse": None,
    "ecmwf-forecast": "MS",
    "era5-pds": None,
    "esa-worldcover": None,
    "fia": None,
    "gap": None,
    "gbif": None,
    "gnatsgo-rasters": None,
    "gnatsgo-tables": None,
    "goes-cmi": "W-MON",
    "hrea": None,
    "io-lulc": None,
    "io-lulc-9-class": None,
    "jrc-gsw": None,
    "landsat-c2-l1": "MS",
    "landsat-c2-l2": "MS",
    "mobi": None,
    "modis-09A1-061": "MS",
    "modis-09Q1-061": "MS",
    "modis-10A1-061": "MS",
    "modis-10A2-061": "MS",
    "modis-11A1-061": "MS",
    "modis-11A2-061": "MS",
    "modis-13A1-061": "MS",
    "modis-13Q1-061": "MS",
    "modis-14A1-061": "MS",
    "modis-14A2-061": "MS",
    "modis-15A2H-061": "MS",
    "modis-15A3H-061": "MS",
    "modis-16A3GF-061": "MS",
    "modis-17A2H-061": "MS",
    "modis-17A2HGF-061": "MS",
    "modis-17A3HGF-061": "MS",
    "modis-21A2-061": "MS",
    "modis-43A4-061": "MS",
    "modis-64A1-061": "MS",
    "mtbs": None,
    "naip": "YS",
    "nasa-nex-gddp-cmip6": None,
    "nasadem": None,
    "noaa-c-cap": None,
    "nrcan-landcover": None,
    "planet-nicfi-analytic": "YS",
    "planet-nicfi-visual": "YS",
    "sentinel-1-grd": "MS",
    "sentinel-1-rtc": "MS",
    "sentinel-2-l2a": "W-MON",
    "us-census": None,
}

SKIP = {
    "daymet-daily-na",
    "daymet-daily-pr",
    "daymet-daily-hi",
    "daymet-monthly-na",
    "daymet-monthly-pr",
    "daymet-monthly-hi",
    "daymet-annual-na",
    "daymet-annual-pr",
    "daymet-annual-hi",
    "terraclimate",
    "gridmet",
    "landsat-8-c2-l2",
    "gpm-imerg-hhr",
    "deltares-floods",
    "goes-mcmip",
    # errors
    "cil-gdpcir-cc0",
    "3dep-lidar-intensity",
    "cil-gdpcir-cc-by",
    "ecmwf-forecast",
    "3dep-lidar-copc",
    "era5-pds",
    "3dep-lidar-classification",
    "3dep-lidar-dtm-native",
    "cil-gdpcir-cc-by-sa",
}

def _pairwise(
    iterable: collections.abc.Iterable,
) -> Any:
    # pairwise('ABCDEFG') --> AB BC CD DE EF FG
    a, b = itertools.tee(iterable)
    next(b, None)
    return zip(a, b)

def _build_output_path(
    base_output_path: str,
    part_number: int | None,
    total: int | None,
    start_datetime: datetime.datetime,
    end_datetime: datetime.datetime,
) -> str:
    a, b = start_datetime, end_datetime
    base_output_path = base_output_path.rstrip("/")

    if part_number is not None and total is not None:
        output_path = (
            f"{base_output_path}/part-{part_number:0{len(str(total * 10))}}_"
            f"{a.isoformat()}_{b.isoformat()}.parquet"
        )
    else:
        token = hashlib.md5(
            "".join([a.isoformat(), b.isoformat()]).encode()
        ).hexdigest()
        output_path = (
            f"{base_output_path}/part-{token}_{a.isoformat()}_{b.isoformat()}.parquet"
        )
    return output_path

def inject_links(item: dict[str, Any]) -> dict[str, Any]:
    item["links"] = [
        {
            "rel": "collection",
            "type": "application/json",
            "href": f"https://planetarycomputer.microsoft.com/api/stac/v1/collections/{item['collection']}",  # noqa: E501
        },
        {
            "rel": "parent",
            "type": "application/json",
            "href": f"https://planetarycomputer.microsoft.com/api/stac/v1/collections/{item['collection']}",  # noqa: E501
        },
        {
            "rel": "root",
            "type": "application/json",
            "href": "https://planetarycomputer.microsoft.com/api/stac/v1/",
        },
        {
            "rel": "self",
            "type": "application/geo+json",
            "href": f"https://planetarycomputer.microsoft.com/api/stac/v1/collections/{item['collection']}/items/{item['id']}",  # noqa: E501
        },
        {
            "rel": "preview",
            "href": f"https://planetarycomputer.microsoft.com/api/data/v1/item/map?collection={item['collection']}&item={item['id']}",  # noqa: E501
            "title": "Map of item",
            "type": "text/html",
        },
    ]
    return item


def inject_assets(item: dict[str, Any], render_config: str | None) -> dict[str, Any]:
    item["assets"]["tilejson"] = {
        "href": (
            "https://planetarycomputer.microsoft.com/api/data/v1/item/tilejson.json?"
            f"collection={item['collection']}"
            f"&item={item['id']}&{render_config}"
        ),
        "roles": ["tiles"],
        "title": "TileJSON with default rendering",
        "type": "application/json",
    }
    item["assets"]["rendered_preview"] = {
        "href": (
            "https://planetarycomputer.microsoft.com/api/data/v1/item/preview.png?"
            f"collection={item['collection']}"
            f"&item={item['id']}&{render_config}"
        ),
        "rel": "preview",
        "roles": ["overview"],
        "title": "Rendered preview",
        "type": "image/png",
    }
    return item

def naip_year_to_int(item: dict[str, Any]) -> dict[str, Any]:
    """Convert the year to an integer."""
    if "naip:year" in item["properties"] and isinstance(item["properties"]["naip:year"], str):
            item["properties"]["naip:year"] = int(item["properties"]["naip:year"])
    return item

def clean_item(item: dict[str, Any], render_config: str | None) -> dict[str, Any]:
    """Clean items by making sure that naip:year is an int and injecting links and assets."""
    item = inject_links(inject_assets(item, render_config))

    if "proj:epsg" in item["properties"] and not item["properties"]["proj:epsg"]:
        # This cannot be null
        item["properties"]["proj:epsg"] = ""

    if item["collection"] == "naip":
        item = naip_year_to_int(item)
    return item

@dataclasses.dataclass
class CollectionConfig:
    """
    Additional collection-based configuration to inject, matching the
    dynamic properties from the API.
    """

    collection_id: str
    partition_frequency: str | None = None
    stac_api: str = "https://planetarycomputer.microsoft.com/api/stac/v1"
    should_inject_dynamic_properties: bool = True
    render_config: str | None = None

    def __post_init__(self) -> None:
        self._collection: pystac.Collection | None = None

    @property
    def collection(self) -> pystac.Collection:
        if self._collection is None:
            self._collection = pystac.read_file(
                f"{self.stac_api}/collections/{self.collection_id}"
            )  # type: ignore
        assert self._collection is not None
        return self._collection

    def generate_endpoints(
        self, since: datetime.datetime | None = None
    ) -> list[tuple[datetime.datetime, datetime.datetime]]:
        if self.partition_frequency is None:
            raise ValueError("Set partition_frequency")

        start_datetime, end_datetime = self.collection.extent.temporal.intervals[0]

        # https://github.com/dateutil/dateutil/issues/349
        if start_datetime and start_datetime.tzinfo == dateutil.tz.tz.tzlocal():
            start_datetime = start_datetime.astimezone(datetime.timezone.utc)

        if end_datetime and end_datetime.tzinfo == dateutil.tz.tz.tzlocal():
            end_datetime = end_datetime.astimezone(datetime.timezone.utc)

        if end_datetime is None:
            end_datetime = pd.Timestamp.utcnow()

        # we need to ensure that the `end_datetime` is past the end of the last partition
        # to avoid missing out on the last partition of data.
        offset = pd.tseries.frequencies.to_offset(self.partition_frequency)

        if not offset.is_on_offset(start_datetime):
            start_datetime = start_datetime - offset

        if not offset.is_on_offset(end_datetime):
            end_datetime = end_datetime + offset

        idx = pd.date_range(start_datetime, end_datetime, freq=self.partition_frequency)

        if since:
            idx = idx[idx >= since]

        pairs = _pairwise(idx)
        return list(pairs)

    def export_partition(
        self,
        conninfo: str,
        output_protocol: str,
        output_path: str,
        start_datetime: datetime.datetime | None = None,
        end_datetime: datetime.datetime | None = None,
        storage_options: dict[str, Any] | None = None,
        rewrite: bool = False,
    ) -> str | None:
        # pass
        fs = fsspec.filesystem(output_protocol, **storage_options)  # type: ignore
        if fs.exists(output_path) and not rewrite:
            logger.debug("Path %s already exists.", output_path)
            return output_path

        def _row_func(item: dict[str, Any]) -> dict[str, Any]:
            return clean_item(item, self.render_config)
        if any(
            pgstac_to_iter(
                conninfo=conninfo,
                collection=self.collection_id,
                start_datetime=start_datetime,
                end_datetime=end_datetime,
                row_func=_row_func,
            )
        ):
            logger.info(f"Running parquet export with chunk size of {CHUNK_SIZE}")
            with tempfile.TemporaryDirectory() as tmpdir:
                arrow = pgstac_to_arrow(
                    conninfo=conninfo,
                    collection=self.collection_id,
                    start_datetime=start_datetime,
                    end_datetime=end_datetime,
                    row_func=_row_func,
                    schema="ChunksToDisk",
                    tmpdir=tmpdir,
                    chunk_size=CHUNK_SIZE
                )

                to_parquet(
                    arrow,
                    output_path,
                    filesystem=fs)
        return output_path

    def export_partition_for_endpoints(
        self,
        endpoints: tuple[datetime.datetime, datetime.datetime],
        conninfo: str,
        output_protocol: str,
        output_path: str,
        storage_options: dict[str, Any],
        part_number: int | None = None,
        total: int | None = None,
        rewrite: bool = False,
        skip_empty_partitions: bool = False,
    ) -> str | None:
        """
        Export results for a pair of endpoints.
        """
        start, end = endpoints
        partition_path = _build_output_path(output_path, part_number, total, start, end)
        return self.export_partition(
            conninfo,
            output_protocol,
            partition_path,
            start_datetime=start,
            end_datetime=end,
            storage_options=storage_options,
            rewrite=rewrite,
        )

    def export_exists(
        self,
        output_protocol: str,
        output_path: str,
        storage_options: dict[str, Any],
    ) -> bool:
        fs = fsspec.filesystem(output_protocol, **storage_options)
        if output_protocol:
            output_path = f"{output_protocol}://{output_path}"
        return fs.exists(output_path)

    def _partition_needs_to_be_rewritten(
        self,
        output_protocol: str,
        output_path: str,
        storage_options: dict[str, Any],
        partition: Partition,
    ) -> bool:
        fs = fsspec.filesystem(output_protocol, **storage_options)
        if output_protocol:
            output_path = f"{output_protocol}://{output_path}"
        if not fs.exists(output_path):
            return True
        file_info = fs.info(output_path)

        # Handle case where last_modified is already a datetime object or a timestamp
        last_modified = file_info["last_modified"]
        if isinstance(last_modified, datetime.datetime):
            file_modified_time = last_modified
        else:
            # Assume it's a timestamp (int/float)
            file_modified_time = datetime.datetime.fromtimestamp(last_modified)
            
        partition_modified_time = partition.last_updated
        return file_modified_time < partition_modified_time

    def export_collection(
        self,
        conninfo: str,
        output_protocol: str,
        output_path: str,
        storage_options: dict[str, Any],
        pgstac_partitions: dict[str, list[Partition]],
        rewrite: bool = False,
        skip_empty_partitions: bool = False,
    ) -> list[str | None]:

        if not self.partition_frequency:
            logger.info("Exporting single-partition collection %s", self.collection_id)

            results = [
                self.export_partition(
                    conninfo,
                    output_protocol,
                    output_path,
                    storage_options=storage_options)
            ]

        elif self.partition_frequency and len(pgstac_partitions[self.collection_id]) == 1:
            endpoints = self.generate_endpoints()
            total = len(endpoints)
            logger.info(
                "Exporting %d partitions for collection %s with frequency %s", total, self.collection_id, self.partition_frequency
            )

            results = []
            for i, endpoint in tqdm.auto.tqdm(enumerate(endpoints), total=total):
                results.append(
                    self.export_partition_for_endpoints(
                        endpoints=endpoint,
                        conninfo=conninfo,
                        output_protocol=output_protocol,
                        output_path=output_path,
                        storage_options=storage_options,
                        rewrite=rewrite,
                        skip_empty_partitions=skip_empty_partitions,
                        part_number=i,
                        total=total,
                    )
                )
        else:
            partitions = pgstac_partitions[self.collection_id]
            total = len(partitions)
            # some collections are not partitioned in pgstac, some are.
            # If a collection is not partition in pgstac, then we will apply the partitioning scheme of the STAC collection
            # In pgstac, you always have to opt-into a partitioning scheme,
            # either None/Monthly/Yearly in the collections table.
            # Ideal size is 10M to 20M rows per partition, but that it dataset dependent.
            logger.info(
                "Exporting %d partitions for collection %s using pgstac partitions", total, self.collection_id
            )

            results = []
            for i, partition in tqdm.auto.tqdm(enumerate(partitions), total=total):
                partition_path = _build_output_path(output_path, i, total, partition.start, partition.end)
                if self._partition_needs_to_be_rewritten(
                    output_protocol=output_protocol,
                    output_path=partition_path,
                    storage_options=storage_options,
                    partition=partition,
                ):
                    results.append(
                        self.export_partition(
                            conninfo=conninfo,
                            output_protocol=output_protocol,
                            output_path=partition_path,
                            start_datetime=partition.start,
                            end_datetime=partition.end,
                            storage_options=storage_options,
                            rewrite=rewrite
                        )
                )
                else:
                    logger.info(
                        "Partition %s already exists and was last updated at %s, skipping",
                        partition_path,
                        partition.last_updated,
                    )
                    results.append(partition_path)

        return results

def build_render_config(render_params: dict[str, Any], assets: dict[str, Any]) -> str:
    flat = []
    if assets:
        for asset in assets:
            flat.append(("assets", asset))

    for k, v in render_params.items():
        if isinstance(v, list):
            flat.extend([(k, v2) for v2 in v])
        else:
            flat.append((k, v))
    return urllib.parse.urlencode(flat)


def generate_configs_from_storage_table(
    table_client: azure.data.tables.TableClient,
) -> dict[str, CollectionConfig]:
    configs = {}
    for entity in table_client.list_entities():
        collection_id = entity["RowKey"]
        data = json.loads(entity["Data"])

        render_params = data["render_config"]["render_params"]
        assets = data["render_config"]["assets"]
        render_config = build_render_config(render_params, assets)
        configs[collection_id] = CollectionConfig(
            collection_id, render_config=render_config
        )

    return configs


def generate_configs_from_api(url: str) -> dict[str, CollectionConfig]:
    configs = {}
    r = requests.get(url)
    r.raise_for_status()

    for collection in r.json()["collections"]:
        partition_frequency = (
            collection["assets"]
            .get("geoparquet-items", {})
            .get("msft:partition_info", {})
            .get("partition_frequency", None)
        )

        configs[collection["id"]] = CollectionConfig(
            collection["id"], partition_frequency=partition_frequency
        )

    return configs


def merge_configs(
    table_configs: dict[str, CollectionConfig], api_configs: dict[str, CollectionConfig]
) -> dict[str, CollectionConfig]:
    # what a mess. Get partitioning config from the API, render from the table.
    configs = {}
    for k in table_configs.keys() | api_configs.keys():
        table_config = table_configs.get(k)
        api_config = api_configs.get(k)
        config = table_config or api_config
        assert config
        if api_config:
            config.partition_frequency = api_config.partition_frequency
        configs[k] = config
    return configs


class StacGeoparquetTaskInput(PCBaseModel):
    table_name: str
    table_account_url: str
    storage_options_account_name: str

    connection_info: str | None = None
    output_protocol: str = "abfs"
    table_credential: str | None = None
    storage_options_credential: str | None = None
    extra_skip: Set[str] | None = None
    collections: str | Set[str] | None = None


class StacGeoparquetTaskOutput(PCBaseModel):
    n_failures: int

class StacGeoparquetTask(Task[StacGeoparquetTaskInput, StacGeoparquetTaskOutput]):
    _input_model = StacGeoparquetTaskInput
    _output_model = StacGeoparquetTaskOutput

    def get_required_environment_variables(self) -> list[str]:
        return ["STAC_GEOPARQUET_CONNECTION_INFO"]

    def run(
        self, input: StacGeoparquetTaskInput, context: TaskContext
    ) -> Union[StacGeoparquetTaskOutput, WaitTaskResult, FailedTaskResult]:

        result = run(
            output_protocol=input.output_protocol,
            connection_info=input.connection_info,
            table_credential=input.table_credential,
            table_name=input.table_name,
            table_account_url=input.table_account_url,
            storage_options_account_name=input.storage_options_account_name,
            storage_options_credential=input.storage_options_credential,
            extra_skip=input.extra_skip,
            collections=input.collections,
        )
        return StacGeoparquetTaskOutput(n_failures=result)


def list_planetary_computer_collection_configs(
    connection_info: str | None = None,
    table_credential: (
        str
        | None
        | azure.core.credentials.TokenCredential
        | azure.core.credentials.AzureSasCredential
    ) = None,
    table_name: str | None = None,
    table_account_url: str | None = None,
    storage_options_account_name: str | None = None,
    storage_options_credential: (
        str | None | azure.core.credentials.TokenCredential
    ) = None,
    extra_skip: Set[str] | None = None,
    collections: str | Set[str] | None = None,
) -> dict[str, CollectionConfig]:
    try:
        connection_info = (
            connection_info or os.environ["STAC_GEOPARQUET_CONNECTION_INFO"]
        )
    except KeyError as e:
        raise KeyError(
            "STAC_GEOPARQUET_CONNECTION_INFO must be set if not explicitly provided"
        ) from e
    table_credential = table_credential or os.environ.get(
        "STAC_GEOPARQUET_TABLE_CREDENTIAL", azure.identity.DefaultAzureCredential()
    )
    assert table_credential is not None
    table_name = table_name or os.environ["STAC_GEOPARQUET_TABLE_NAME"]
    table_account_url = (
        table_account_url or os.environ["STAC_GEOPARQUET_TABLE_ACCOUNT_URL"]
    )
    storage_options_account_name = (
        storage_options_account_name
        or os.environ["STAC_GEOPARQUET_STORAGE_OPTIONS_ACCOUNT_NAME"]
    )
    storage_options_credential = storage_options_credential or os.environ.get(
        "STAC_GEOPARQUET_STORAGE_OPTIONS_CREDENTIAL",
        azure.identity.DefaultAzureCredential(),
    )

    extra_skip = extra_skip or set()
    skip = SKIP | extra_skip

    if isinstance(table_credential, str):
        table_credential = azure.core.credentials.AzureSasCredential(table_credential)

    table_client = azure.data.tables.TableClient(
        table_account_url,
        table_name,
        credential=table_credential,
    )
    logger.info(f"Connecting to table {table_name} at {table_account_url}")
    configs = get_configs(table_client)

    if collections is None:
        configs = {k: v for k, v in configs.items() if k not in skip}
    elif isinstance(collections, str):
        configs = {k: v for k, v in configs.items() if k == collections}
    elif isinstance(collections, set):
        configs = {k: v for k, v in configs.items() if k in collections}

    return configs

def get_configs(table_client: azure.data.tables.TableClient) -> dict[str, CollectionConfig]:
    table_configs = generate_configs_from_storage_table(table_client)
    api_configs = generate_configs_from_api(
        "https://planetarycomputer.microsoft.com/api/stac/v1/collections"
    )
    configs = merge_configs(table_configs, api_configs)
    for k, v in configs.items():
        if v.partition_frequency is None:
            v.partition_frequency = PARTITION_FREQUENCIES.get(k)

    return configs

def run(
    output_protocol: str = "abfs",
    connection_info: str | None = None,
    table_credential: (
        str
        | None
        | azure.core.credentials.TokenCredential
        | azure.core.credentials.AzureSasCredential
    ) = None,
    table_name: str | None = None,
    table_account_url: str | None = None,
    storage_options_account_name: str | None = None,
    storage_options_credential: (
        str | None | azure.core.credentials.TokenCredential
    ) = None,
    extra_skip: Set[str] | None = None,
    collections: str | Set[str] | None = None,
    configs: dict[str, CollectionConfig] | None = None,
) -> int:
    if configs is None:
        configs = list_planetary_computer_collection_configs(
            connection_info=connection_info,
            table_credential=table_credential,
            table_name=table_name,
            table_account_url=table_account_url,
            storage_options_account_name=storage_options_account_name,
            storage_options_credential=storage_options_credential,
            extra_skip=extra_skip,
            collections=collections,
        )
    try:
        connection_info = (
            connection_info or os.environ["STAC_GEOPARQUET_CONNECTION_INFO"]
        )
    except KeyError as e:
        raise KeyError(
            "STAC_GEOPARQUET_CONNECTION_INFO must be set if not explicitly provided"
        ) from e
    table_credential = table_credential or os.environ.get(
        "STAC_GEOPARQUET_TABLE_CREDENTIAL", azure.identity.DefaultAzureCredential()
    )
    assert table_credential is not None
    table_name = table_name or os.environ["STAC_GEOPARQUET_TABLE_NAME"]
    table_account_url = (
        table_account_url or os.environ["STAC_GEOPARQUET_TABLE_ACCOUNT_URL"]
    )
    storage_options_account_name = (
        storage_options_account_name
        or os.environ["STAC_GEOPARQUET_STORAGE_OPTIONS_ACCOUNT_NAME"]
    )
    storage_options_credential = storage_options_credential or os.environ.get(
        "STAC_GEOPARQUET_STORAGE_OPTIONS_CREDENTIAL",
        azure.identity.DefaultAzureCredential(),
    )

    storage_options = {
        "account_name": storage_options_account_name,
        "credential": storage_options_credential,
    }

    N = len(configs)
    success = []
    failure = []

    collection_partitions = list(get_pgstac_partitions(conninfo=connection_info))
    recent_collection_updates: dict[str, list[Partition]] = {}
    for partition in collection_partitions:
        recent_collection_updates.setdefault(partition.collection, []).append(partition)
    logger.info(f"Found {len(collection_partitions)} pgstac partitions")

    for i, config in enumerate(configs.values(), 1):
        output_path=f"items/{config.collection_id}.parquet"
        try:
            t0 = time.monotonic()
            config.export_collection(
                connection_info,
                output_protocol,
                output_path,
                storage_options,
                pgstac_partitions=recent_collection_updates,
                skip_empty_partitions=True,
                rewrite=True
            )
            t1 = time.monotonic()
            logger.info(f"Completed {config.collection_id} [{i}/{N}] in {t1-t0:.2f}s")
        except Exception as e:
            failure.append((config.collection_id, e))
            logger.exception(f"Failed processing {config.collection_id}")
        else:
            success.append(config.collection_id)

    return len(failure)

if __name__ == "__main__":
    # Remove all handlers associated with the root logger object.
    for h in logging.root.handlers[:]:
        logging.root.removeHandler(h)
    # Set up logging only for this file and stac_geoparquet package
    logging.basicConfig(handlers=[handler], level=logging.DEBUG, force=True)
    logging.getLogger().setLevel(logging.WARNING)
    logger.setLevel(logging.DEBUG)
    logging.getLogger("stac_geoparquet").setLevel(logging.DEBUG)
    parser = argparse.ArgumentParser(description="Export STAC collection to GeoParquet.")
    parser.add_argument(
        "--collection",
        type=str,
        required=False,
        help="The collection ID to export."
    )
    args = parser.parse_args()
    configs = list_planetary_computer_collection_configs(
        connection_info=os.environ["STAC_GEOPARQUET_CONNECTION_INFO"],
        table_credential=azure.identity.DefaultAzureCredential(),
        table_name=os.environ["STAC_GEOPARQUET_TABLE_NAME"],
        table_account_url=os.environ["STAC_GEOPARQUET_TABLE_ACCOUNT_URL"],
        storage_options_account_name=os.environ["STAC_GEOPARQUET_STORAGE_OPTIONS_ACCOUNT_NAME"],
        storage_options_credential=azure.identity.DefaultAzureCredential(),
        extra_skip=SKIP,
        collections=args.collection,
    )
    n_failures = run(collections=args.collection, configs=configs)
    if n_failures == 0:
        logger.info("Export completed successfully.")
    else:
        logger.error(f"Export completed with {n_failures} failures.")
