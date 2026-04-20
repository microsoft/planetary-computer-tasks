# stac-geoparquet

Generates the `stac-geoparquet` collection-level assets for the [Planetary Computer](https://planetarycomputer.microsoft.com/docs/quickstarts/stac-geoparquet/).

## Container Images

Test the build with;
```shell
docker build -t stac-geoparquet -f datasets/stac-geoparquet/Dockerfile .
```

Then publish to the ACR with:

```shell
az acr build -r pccomponents -t pctasks-stac-geoparquet:latest -t pctasks-stac-geoparquet:2023.7.10.0 -f datasets/stac-geoparquet/Dockerfile .
```

## Permissions

This requires the following permissions

* Storage Data Table Reader on the config tables (`pcapi/bluecollectionconfig`, `pcapi/greencollectionconfig`)
* Storage Blob Data Contributor on the `pcstacitems` container.

## Arguments

By default, this workflow will generate geoparquet assets for all collections.
If you want to select a subset of collections, you can use either:

1. `extra_skip`: This will skip certain collections
1. `collections`: This will only generate geoparquet for the specified collection(s).

## Updates

The workflow used for updates was registered with

```shell
pctasks workflow update datasets/stac-geoparquet/workflow.yaml
```

It can be manually invoked with:

```shell
pctasks workflow submit stac-geoparquet
```

## Run Locally

You can debug the geoparquet export locally like this:

```shell
export STAC_GEOPARQUET_CONNECTION_INFO="secret"
export STAC_GEOPARQUET_TABLE_NAME="greencollectionconfig"
export STAC_GEOPARQUET_TABLE_ACCOUNT_URL="https://pcapi.table.core.windows.net"
export STAC_GEOPARQUET_STORAGE_OPTIONS_ACCOUNT_NAME="pcstacitems"

python3 pc_stac_geoparquet.py --collection hls2-l30
```

Apart from the Postgres connection string, you will need PIM activations for
`Storage Blob Data Contributor` to be able to write to the production storage account.
