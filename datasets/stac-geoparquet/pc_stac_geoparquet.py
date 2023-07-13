from __future__ import annotations

import argparse
import logging
import os
from typing import Union, Set

import azure.core.credentials
import azure.data.tables
import azure.identity
from stac_geoparquet import pc_runner

from pctasks.task.task import Task
from pctasks.core.models.base import PCBaseModel
from pctasks.core.models.task import FailedTaskResult, WaitTaskResult
from pctasks.task.context import TaskContext


handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("[%(levelname)s]:%(asctime)s: %(message)s"))
handler.setLevel(logging.INFO)
logger = logging.getLogger(__name__)
logger.addHandler(handler)
logger.setLevel(logging.INFO)


class StacGeoparquetTaskInput(PCBaseModel):
    table_name: str
    table_account_url: str
    storage_options_account_name: str

    connection_info: str | None = None
    output_protocol: str = "abfs"
    table_credential: str | None = None
    storage_options_credential: str | None = None
    extra_skip: Set[str] | None = None


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
        )
        return StacGeoparquetTaskOutput(n_failures=result)


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


def run(
    output_protocol: str = "abfs",
    connection_info: str | None = None,
    table_credential: str
    | None
    | azure.core.credentials.TokenCredential
    | azure.core.credentials.AzureSasCredential = None,
    table_name: str | None = None,
    table_account_url: str | None = None,
    storage_options_account_name: str | None = None,
    storage_options_credential: str
    | None
    | azure.core.credentials.TokenCredential = None,
    extra_skip: Set[str] | None = None,
) -> int:
    # handle the arguments
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
    configs = pc_runner.get_configs(table_client)

    configs = {k: v for k, v in configs.items() if k not in skip}
    storage_options = {
        "account_name": storage_options_account_name,
        "credential": storage_options_credential,
    }

    def f(config: pc_runner.CollectionConfig) -> None:
        config.export_collection(
            connection_info,
            output_protocol,
            f"items/{config.collection_id}.parquet",
            storage_options,
            skip_empty_partitions=True,
        )

    N = len(configs)
    success = []
    failure = []

    for i, config in enumerate(configs.values(), 1):
        logger.info(f"processing {config.collection_id} [{i}/{N}]")
        try:
            f(config)
        except Exception as e:
            failure.append((config.collection_id, e))
            logger.exception(f"Failed processing {config.collection_id}")
        else:
            success.append(config.collection_id)

    return len(failure)
