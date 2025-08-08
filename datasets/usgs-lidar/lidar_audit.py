import os
from pctasks.core.models.base import PCBaseModel
from pctasks.task.context import TaskContext
from pctasks.task.task import Task
from pctasks.core.utils.credential import get_credential
from pydantic import BaseModel
from typing import List
import adlfs
import geopandas
import logging
import planetary_computer
import pyarrow.fs
import rasterio
import rasterio.crs
import rasterio.warp
import shapely
from opencensus.ext.azure.log_exporter import AzureEventHandler, AzureLogHandler

logger = logging.getLogger(f"lidar-audit-logger")


instrumentation_key = os.environ.get("APPINSIGHTS_INSTRUMENTATIONKEY")
if instrumentation_key:  # Set up traces logging.
    logger.setLevel(logging.INFO)
    traces_handler = AzureLogHandler(
        connection_string=f"InstrumentationKey={instrumentation_key}"
    )
    logger.addHandler(traces_handler)
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.INFO)
    logger.addHandler(stream_handler)


class ParquetEnumerationInput(PCBaseModel):
    parquet_prefix: str


class ParquetEnumerationOutput(PCBaseModel):
    parquet_partition_urls: List[str]


class ParquetEnumerationTask(Task[ParquetEnumerationInput, ParquetEnumerationOutput]):
    _input_model = ParquetEnumerationInput
    _output_model = ParquetEnumerationOutput

    def run(
        self, input: ParquetEnumerationInput, context: TaskContext
    ) -> ParquetEnumerationOutput:
        fs = adlfs.AzureBlobFileSystem(
            account_name="pcstacitems",
            credential=get_credential(),
        )
        parquet_files = fs.ls(input.parquet_prefix)
        parquet_urls = [f"az://{f}" for f in parquet_files]
        logger.info(
            f"Found {len(parquet_urls)} parquet files for prefix {input.parquet_prefix}"
        )
        return ParquetEnumerationOutput(parquet_partition_urls=parquet_urls)


class LidarAuditInput(PCBaseModel):
    parquet_url: str


class LidarAuditOutput(PCBaseModel):
    csv_url: str


class LidarAudit(Task[LidarAuditInput, LidarAuditOutput]):
    _input_model = LidarAuditInput
    _output_model = LidarAuditOutput

    def run(self, input: LidarAuditInput, context: TaskContext) -> LidarAuditOutput:
        # URI must look like "az://items/3dep-lidar-hag.parquet/part-000_2012-01-01T00:00:00+00:00_2013-01-01T00:00:00+00:00.parquet",
        parquet_storage_options = dict(
            account_name="pcstacitems",
            credential=get_credential(),
        )
        parquet_url = input.parquet_url
        df = geopandas.read_parquet(
            parquet_url,
            storage_options=parquet_storage_options,
            columns=["geometry", "assets", "id", "3dep:usgs_id"],
        )

        self.compute_similarities(df)
        output_name = parquet_url.split("/")[-1].replace(".parquet", ".csv")
        output_url = f"az://usgs-lidar-etl-data/audit/{output_name}"
        self.write_to_csv(df, output_url)
        return LidarAuditOutput(csv_url=output_url)

    def write_to_csv(self, df: geopandas.GeoDataFrame, output_url: str) -> None:
        etl_storage_options = dict(
            account_name="usgslidareuwest",
            credential=get_credential(),
        )
        logger.info(f"Writing audit output to {output_url}.")
        df.to_csv(
            output_url,
            storage_options=etl_storage_options,
        )

    def compute_similarities(self, df: geopandas.GeoDataFrame) -> None:
        cog_geometries = []
        dst_crs = rasterio.crs.CRS.from_epsg(4326)

        for asset in df["assets"].tolist():
            # This href points to a COG asset which does not allow anonymous access.
            # Calling planetary_computer.sign requests a short-lived SAS token for the asset.
            signed_asset = planetary_computer.sign(asset["data"]["href"])
            with rasterio.open(
                signed_asset,
            ) as cog:
                cog_geometries.append(
                    shapely.geometry.box(
                        *rasterio.warp.transform_bounds(cog.crs, dst_crs, *cog.bounds)
                    )
                )

        df["cog_geometry"] = geopandas.GeoSeries(
            cog_geometries, index=df.index, crs=dst_crs
        )
        df["envelope"] = df["geometry"].envelope
        df["similarity"] = (
            df["cog_geometry"].intersection(df["envelope"]).area
            / df["cog_geometry"].union(df["envelope"]).area
        )
