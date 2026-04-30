"""
STAC Tools for gbif
"""
import copy
import enum
import logging
from typing import TypeVar

import dask
import pystac
import pandas as pd
import pyarrow
import pyarrow.parquet
import fsspec
import dask_geopandas
import shapely.geometry
import datetime

COLUMN_DESCRIPTIONS = {
    "gbifid": "GBIF's identifier for the occurrence",
    "datasetkey": "GBIF's UUID for the [dataset](https://www.gbif.org/developer/registry#datasets) containing this occurrence",
    "publishingorgkey": "GBIF's UUID for the [organization](https://www.gbif.org/developer/registry#organizations) publishing this occurrence.",
    "occurrencestatus": "See [dwc:occurrenceStatus](https://dwc.tdwg.org/terms/#occurrenceStatus). Either the value `PRESENT` or `ABSENT`.  **Many users will wish to filter for `PRESENT` data.**",
    "basisofrecord": "See [dwc:basisOfRecord](https://dwc.tdwg.org/terms/#basisOfRecord).  One of `PRESERVED_SPECIMEN`, `FOSSIL_SPECIMEN`, `LIVING_SPECIMEN`, `OBSERVATION`, `HUMAN_OBSERVATION`, `MACHINE_OBSERVATION`, `MATERIAL_SAMPLE`, `LITERATURE`, `UNKNOWN`.",
    "kingdom": "See [dwc:kingdom](https://dwc.tdwg.org/terms/#kingdom).  This field has been aligned with the [GBIF backbone taxonomy](https://doi.org/10.15468/39omei).",
    "phylum": "See [dwc:phylum](https://dwc.tdwg.org/terms/#phylum).  This field has been aligned with the GBIF backbone taxonomy.",
    "class": "See [dwc:class](https://dwc.tdwg.org/terms/#class).  This field has been aligned with the GBIF backbone taxonomy.",
    "order": "See [dwc:order](https://dwc.tdwg.org/terms/#order).  This field has been aligned with the GBIF backbone taxonomy.",
    "family": "See [dwc:family](https://dwc.tdwg.org/terms/#family).  This field has been aligned with the GBIF backbone taxonomy.",
    "genus": "See [dwc:genus](https://dwc.tdwg.org/terms/#genus).  This field has been aligned with the GBIF backbone taxonomy.",
    "species": "See [dwc:species](https://dwc.tdwg.org/terms/#species).  This field has been aligned with the GBIF backbone taxonomy.",
    "infraspecificepithet": "See [dwc:infraspecificEpithet](https://dwc.tdwg.org/terms/#infraspecificEpithet).  This field has been aligned with the GBIF backbone taxonomy.",
    "taxonrank": "See [dwc:taxonRank](https://dwc.tdwg.org/terms/#taxonRank).  This field has been aligned with the GBIF backbone taxonomy.",
    "scientificname": "See [dwc:scientificName](https://dwc.tdwg.org/terms/#scientificName).  This field has been aligned with the GBIF backbone taxonomy.",
    "verbatimscientificname": "The scientific name as provided by the data publisher",
    "verbatimscientificnameauthorship": "The scientific name authorship provided by the data publisher.",
    "taxonkey": "The numeric identifier for the [taxon](https://www.gbif.org/developer/species#nameUsages) in GBIF's backbone taxonomy corresponding to `scientificname`.",
    "specieskey": "The numeric identifier for the taxon in GBIF's backbone taxonomy corresponding to `species`.",
    "typestatus": "See [dwc:typeStatus](https://dwc.tdwg.org/terms/#typeStatus).",
    "countrycode": "See [dwc:countryCode](https://dwc.tdwg.org/terms/#countryCode).  GBIF's interpretation has set this to an ISO 3166-2 code.",
    "locality": "See [dwc:locality](https://dwc.tdwg.org/terms/#locality).",
    "stateprovince": "See [dwc:stateProvince](https://dwc.tdwg.org/terms/#stateProvince).",
    "decimallatitude": "See [dwc:decimalLatitude](https://dwc.tdwg.org/terms/#decimalLatitude).  GBIF's interpretation has normalized this to a WGS84 coordinate.",
    "decimallongitude": "See [dwc:decimalLongitude](https://dwc.tdwg.org/terms/#decimalLongitude).  GBIF's interpretation has normalized this to a WGS84 coordinate.",
    "coordinateuncertaintyinmeters": "See [dwc:coordinateUncertaintyInMeters](https://dwc.tdwg.org/terms/#coordinateUncertaintyInMeters).",
    "coordinateprecision": "See [dwc:coordinatePrecision](https://dwc.tdwg.org/terms/#coordinatePrecision).",
    "elevation": "See [dwc:elevation](https://dwc.tdwg.org/terms/#elevation).  If provided by the data publisher, GBIF's interpretation has normalized this value to metres.",
    "elevationaccuracy": "See [dwc:elevationAccuracy](https://dwc.tdwg.org/terms/#elevationAccuracy).  If provided by the data publisher, GBIF's interpretation has normalized this value to metres.",
    "depth": "See [dwc:depth](https://dwc.tdwg.org/terms/#depth).  If provided by the data publisher, GBIF's interpretation has normalized this value to metres.",
    "depthaccuracy": "See [dwc:depthAccuracy](https://dwc.tdwg.org/terms/#depthAccuracy).  If provided by the data publisher, GBIF's interpretation has normalized this value to metres.",
    "eventdate": "See [dwc:eventDate](https://dwc.tdwg.org/terms/#eventDate).  GBIF's interpretation has normalized this value to an ISO 8601 date with a local time.",
    "year": "See [dwc:year](https://dwc.tdwg.org/terms/#year).",
    "month": "See [dwc:month](https://dwc.tdwg.org/terms/#month).",
    "day": "See [dwc:day](https://dwc.tdwg.org/terms/#day).",
    "individualcount": "See [dwc:individualCount](https://dwc.tdwg.org/terms/#individualCount).",
    "establishmentmeans": "See [dwc:establishmentMeans](https://dwc.tdwg.org/terms/#establishmentMeans).",
    "occurrenceid": "See [dwc:occurrenceID](https://dwc.tdwg.org/terms/#occurrenceID).",
    "institutioncode": "See [dwc:institutionCode](https://dwc.tdwg.org/terms/#institutionCode).",
    "collectioncode": "See [dwc:collectionCode](https://dwc.tdwg.org/terms/#collectionCode).",
    "catalognumber": "See [dwc:catalogNumber](https://dwc.tdwg.org/terms/#catalogNumber).",
    "recordnumber": "See [dwc:recordNumber](https://dwc.tdwg.org/terms/#recordNumber).",
    "recordedby": "See [dwc:recordedBy](https://dwc.tdwg.org/terms/#recordedBy).",
    "identifiedby": "See [dwc:identifiedBy](https://dwc.tdwg.org/terms/#identifiedBy).",
    "dateidentified": "See [dwc:dateIdentified](https://dwc.tdwg.org/terms/#dateIdentified). An ISO 8601 date.",
    "mediatype": "See [dwc:mediaType](https://dwc.tdwg.org/terms/#mediaType).  May contain `StillImage`, `MovingImage` or `Sound` (from [enumeration](http://api.gbif.org/v1/enumeration/basic/MediaType), detailing whether the occurrence has this media available.",
    "issue": "A list of [issues](https://gbif.github.io/gbif-api/apidocs/org/gbif/api/vocabulary/OccurrenceIssue.html) encountered by GBIF in processing this record. More details are available on these issues and flags in [this blog post](https://data-blog.gbif.org/post/issues-and-flags/).",
    "license": "See [dwc:license](https://dwc.tdwg.org/terms/#license). Either [`CC0_1_0`](https://creativecommons.org/publicdomain/zero/1.0/), [`CC_BY_4_0`](https://creativecommons.org/licenses/by/4.0/), or (`CC_BY_NC_4_0`)[https://creativecommons.org/licenses/by-nc/4.0/].",
    "rightsholder": "See [dwc:rightsHolder](https://dwc.tdwg.org/terms/#rightsHolder).",
    "lastinterpreted": "The ISO 8601 date when the record was last processed by GBIF. Data are reprocessed for several reasons, including changes to the backbone taxonomy, so this date is not necessarily the date the occurrence record last changed.",
}

logger = logging.getLogger(__name__)

T = TypeVar("T", pystac.Collection, pystac.Item)
SCHEMA_URI = "https://stac-extensions.github.io/table/v1.2.0/schema.json"
# https://issues.apache.org/jira/browse/PARQUET-1889: parquet doesn't officially
# have a type yet.
PARQUET_MEDIA_TYPE = "application/x-parquet"


def create_item(asset_href: str, storage_options=None, asset_extra_fields=None) -> pystac.Item:
    """
    Create a STAC item for a GBIF Parquet Dataset.

    Parameters
    ----------
    asset_href : str
        The path, including fsspec protocol if necessary, to the root of the parquet datasets.
    storage_options: dict[str, Any], optional
        Storage options used when creating the fsspec filesystem to read the metadata
    asset_extra_fields:
        Additional fields to include in the asset.

    Examples
    --------
    >>> create_item(
    ...     "az://gbif/occurrence/2021-04-13/occurrence.parquet",
    ...     storage_options=dict(account_name="ai4edataeuwest")
    ... )
    """
    date = datetime.datetime(*list(map(int, asset_href.split("/")[-2].split("-"))))
    date_id = f"{date:%Y-%m-%d}"

    item = pystac.Item(
        f"gbif-{date_id}",
        geometry={
            "type": "Polygon",
            "coordinates": [
                [
                    [180.0, -90.0],
                    [180.0, 90.0],
                    [-180.0, 90.0],
                    [-180.0, -90.0],
                    [180.0, -90.0],
                ]
            ],
        },
        bbox=[-180, -90, 180, 90],
        datetime=date,
        properties={},
    )

    result = generate(
        asset_href,
        item,
        storage_options=storage_options,
        proj=False,
        asset_extra_fields=asset_extra_fields,
        count_rows=False,
    )

    for column in result.properties["table:columns"]:
        column["description"] = COLUMN_DESCRIPTIONS[column["name"]]

    result.validate()
    return result


def create_collection(asset_extra_fields=None):
    asset_extra_fields = asset_extra_fields or {}

    collection = pystac.Collection(
        "gbif",
        description="{{ collection.description }}",
        extent=pystac.Extent(
            spatial=pystac.collection.SpatialExtent([[-180, -90, 180, 90]]),
            temporal=pystac.collection.TemporalExtent([datetime.datetime(2021, 4, 13), None]),
        ),
    )
    # collection.extra_fields["table:columns"] = result.properties["table:columns"]
    collection.title = "Global Biodiversity Information Facility (GBIF)"

    pystac.extensions.item_assets.ItemAssetsExtension.add_to(collection)
    collection.extra_fields["item_assets"] = {
        "data": {
            "type": PARQUET_MEDIA_TYPE,
            "title": "Dataset root",
            "roles": ["data"],
            **asset_extra_fields,
        }
    }

    collection.stac_extensions.append(SCHEMA_URI)
    collection.keywords = ["GBIF", "Biodiversity", "Species"]
    collection.extra_fields["msft:short_description"] = (
        "An international network and data infrastructure funded by the world's "
        "governments providing global data that document the occurrence of species."
    )
    collection.extra_fields["msft:container"] = "gbif"
    collection.extra_fields["msft:storage_account"] = "ai4edataeuwest"
    collection.providers = [
        pystac.Provider(
            "Global Biodiversity Information Facility",
            roles=[
                pystac.provider.ProviderRole.PRODUCER,
                pystac.provider.ProviderRole.LICENSOR,
                pystac.provider.ProviderRole.PROCESSOR,
            ],
            url="https://www.gbif.org/",
        ),
        # pystac.Provider(
        #     "Microsoft",
        #     roles=[pystac.provider.ProviderRole.HOST],
        #     url="https://planetarycomputer.microsoft.com",
        # ),
    ]
    # collection.assets["thumbnail"] = pystac.Asset(
    #     title="Forest Inventory and Analysis",
    #     href=(
    #         "https://ai4edatasetspublicassets.blob.core.windows.net/"
    #         "assets/pc_thumbnails/gbif.png"
    #     ),
    #     media_type="image/png",
    # )
    collection.links = [
        pystac.Link(
            pystac.RelType.LICENSE,
            target="https://www.gbif.org/terms",
            media_type="text/html",
            title="Terms of use",
        )
    ]
    # collection.validate()
    return collection

class InferDatetimeOptions(str, enum.Enum):
    no = "no"
    midpoint = "midpoint"
    unique = "unique"
    range = "range"


def generate(
    uri: str,
    template,
    infer_bbox=None,
    infer_geometry=False,
    datetime_column=None,
    infer_datetime=InferDatetimeOptions.no,
    count_rows=True,
    asset_key="data",
    asset_extra_fields=None,
    proj=True,
    storage_options=None,
    validate=True,
) -> T:
    """
    Generate a STAC Item from a Parquet Dataset.

    Parameters
    ----------
    uri : str
        The fsspec-compatible URI pointing to the input table to generate a
        STAC item for.
    template : pystac.Item
        The template item. This will be cloned and new data will be filled in.
    infer_bbox : str, optional
        The column name to use setting the Item's bounding box.

        .. note::

           If the dataset doesn't provide spatial partitions, this will
           require computation.

    infer_geometry: bool, optional
        Whether to fill the item's `geometry` field with the union of the
        geometries in the `infer_bbox` column.

    datetime_column: str, optional
        The column name to use when setting the Item's `datetime` or
        `start_datetime` and `end_datetime` properties. The method used is
        determined by `infer_datetime`.

    infer_datetime: str, optional.
        The method used to find a datetime from the values in `datetime_column`.
        Use the options in the `InferDatetimeOptions` enum.

        - no : do not infer a datetime
        - midpoint : Set `datetime` to the midpoint of the highest and lowest values.
        - unique : Set `datetime` to the unique value. Raises if more than one
          unique value is found.
        - range : Set `start_datetime` and `end_datetime` to the minimum and
          maximum values.

    count_rows : bool, default True
        Whether to add the row count to `table:row_count`.

    asset_key : str, default "data"
        The asset key to use for the parquet dataset. The href will be the ``uri`` and
        the roles will be ``["data"]``.

    asset_extra_fields : dict, optional
        Additional fields to set in the asset's ``extra_fields``.

    proj : bool or dict, default True
        Whether to extract projection information from the dataset and store it
        using the `projection` extension.

        By default, just `proj:crs` is extracted. If `infer_bbox` or `infer_geometry`
        are specified, those will be set as well.

        Alternatively, provide a dict of values to include.

    storage_options: mapping, optional
        A dictionary of keywords to provide to :meth:`fsspec.get_fs_token_paths`
        when creating an fsspec filesystem with a str ``ds``.

    validate : bool, default True
        Whether to validate the returned pystac.Item.

    Returns
    -------
    pystac.Item
        The updated pystac.Item with the following fields set

        * stac_extensions : added `table` extension
        * table:columns

    Examples
    --------

    This example generates a STAC item based on the "naturalearth_lowres" datset
    from geopandas. There's a bit of setup.

    >>> import datetime, geopandas, pystac, stac_table
    >>> gdf = geopandas.read_file(geopandas.datasets.get_path("naturalearth_lowres"))
    >>> gdf.to_parquet("data.parquet")

    Now we can create the item.

    >>> # Create the template Item
    >>> item = pystac.Item(
    ...     "naturalearth_lowres",
    ...     geometry=None,
    ...     bbox=None,
    ...     datetime=datetime.datetime(2021, 1, 1),
    ...     properties={},
    ... )
    >>> result = stac_table.generate("data.parquet", item)
    >>> result
    <Item id=naturalearth_lowres>
    """
    template = copy.deepcopy(template)

    data = None
    storage_options = storage_options or {}
    # data = dask_geopandas.read_parquet(
    #     ds, storage_options=storage_options
    # )
    ds = parquet_dataset_from_url(uri, storage_options)

    if (
        infer_bbox
        or infer_geometry
        or infer_datetime != InferDatetimeOptions.no
        or proj is True
    ):
        data = dask_geopandas.read_parquet(uri, storage_options=storage_options)
    #     # TODO: this doesn't actually work
    #     data = dask_geopandas.read_parquet(
    #         ds.files, storage_options={"filesystem": ds.filesystem}
    #     )

    columns = get_columns(ds)
    template.properties["table:columns"] = columns

    if proj is True:
        proj = get_proj(data)
    proj = proj or {}

    # TODO: Add schema when published
    if SCHEMA_URI not in template.stac_extensions:
        template.stac_extensions.append(SCHEMA_URI)
    if proj and pystac.extensions.projection.SCHEMA_URI not in template.stac_extensions:
        template.stac_extensions.append(pystac.extensions.projection.SCHEMA_URI)

    extra_proj = {}
    if infer_bbox:
        bbox = data.spatial_partitions.unary_union.bounds
        # TODO: may need to convert to epsg:4326
        extra_proj["proj:bbox"] = bbox
        template.bbox = bbox

    if infer_geometry:
        geometry = shapely.geometry.mapping(data.unary_union.compute())
        # TODO: may need to convert to epsg:4326
        extra_proj["proj:geometry"] = geometry
        template.geometry = geometry

    if infer_bbox and template.geometry is None:
        # If bbox is set then geometry must be set as well.
        template.geometry = shapely.geometry.mapping(
            shapely.geometry.box(*template.bbox)
        )

    if infer_geometry and template.bbox is None:
        template.bbox = shapely.geometry.shape(template.geometry).bounds

    if proj or extra_proj:
        template.properties.update(**extra_proj, **proj)

    if infer_datetime != InferDatetimeOptions.no and datetime_column is None:
        raise ValueError("Must specify 'datetime_column' when 'infer_datetime != no'.")

    if infer_datetime == InferDatetimeOptions.midpoint:
        values = dask.compute(data[datetime_column].min(), data[datetime_column].max())
        template.properties["datetime"] = pd.Series(values).mean().to_pydatetime()

    if infer_datetime == InferDatetimeOptions.unique:
        values = data[datetime_column].unique().compute()
        n = len(values)
        if n > 1:
            raise ValueError(f"infer_datetime='unique', but {n} unique values found.")
        template.properties["datetime"] = values[0].to_pydatetime()

    if infer_datetime == InferDatetimeOptions.range:
        values = dask.compute(data[datetime_column].min(), data[datetime_column].max())
        values = list(pd.Series(values).dt.to_pydatetime())
        template.properties["start_datetime"] = values[0].isoformat() + "Z"
        template.properties["end_datetime"] = values[1].isoformat() + "Z"

    if count_rows:
        template.properties["table:row_count"] = sum(
            x.count_rows() for x in ds.fragments
        )

    if asset_key:
        asset = pystac.asset.Asset(
            uri,
            title="Dataset root",
            media_type=PARQUET_MEDIA_TYPE,
            roles=["data"],
            # extra_fields={"table:storage_options": asset_extra_fields},
            extra_fields=asset_extra_fields,
        )
        template.add_asset(asset_key, asset)

    if validate:
        template.validate()

    return template


def get_proj(ds):
    """
    Read projection information from the dataset.
    """
    # Use geopandas to get the proj info
    proj = {}
    maybe_crs = ds.geometry.crs
    if maybe_crs:
        maybe_epsg = ds.geometry.crs.to_epsg()
        if maybe_epsg:
            proj["proj:epsg"] = maybe_epsg
        else:
            proj["proj:wkt2"] = ds.geometry.crs.to_wkt()

    return proj


def get_columns(ds: pyarrow.parquet.ParquetDataset) -> list:
    columns = []
    fragment = ds.fragments[0]

    for field, col in zip(ds.schema, fragment.metadata.schema):
        if field.name == "__null_dask_index__":
            continue

        column = {"name": field.name, "type": col.physical_type.lower()}
        if field.metadata is not None:
            column["metadata"] = field.metadata
        columns.append(column)
    return columns


def parquet_dataset_from_url(
    url: str, storage_options
):
    fs, _, _ = fsspec.get_fs_token_paths(url, storage_options=storage_options)
    pa_fs = pyarrow.fs.PyFileSystem(pyarrow.fs.FSSpecHandler(fs))
    url2 = url.split("://", 1)[-1]  # pyarrow doesn't auto-strip the prefix.
    ds = pyarrow.parquet.ParquetDataset(
        url2, filesystem=pa_fs
    )
    return ds
