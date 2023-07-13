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