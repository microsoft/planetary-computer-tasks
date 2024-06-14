# stac-geoparquet

Generates the `stac-geoparquet` collection-level assets for the [Planetary Computer](https://planetarycomputer.microsoft.com/docs/quickstarts/stac-geoparquet/).

## Container Images

```shell
$ az acr build -r pccomponents -t pctasks-stac-geoparquet:latest -t pctasks-stac-geoparquet:2023.7.10.0 -f datasets/stac-geoparquet/Dockerfile .
```

## Permissions

This requires the following permissions

* Storage Data Table Reader on the config tables (`pcapi/bluecollectoinconfig`, `pcapi/greencollectionconfig`)
* Storage Blob Data Contributor on the `pcstacitems` container.

## Arguments
By default, this workflow will generate geoparquet assets for all collections.
If you want to select a subset of collections, you can use either:
1. `extra_skip`: This will skip certain collections
1. `collections`: This will only generate geoparquet for the specified collection(s).

## Updates

The workflow used for updates was registered with

```
pctasks workflow update datasets/workflows/stac-geoparquet.yaml
```