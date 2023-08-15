# planetary-computer-tasks dataset: sentinel-1-rtc

STAC Items are built from existing STAC Items in the blob://sentinel1euwest/s1-grd-rtc-stac/ container.

## Chunking for dynamic ingest

- Requires an extra `--arg year-prefix {year}` argument when running `pctasks dataset create-chunks` or `pctasks dataset process-items` commands.
- Asset chunkfile creation takes about 5 minutes.

## Docker image

To build and push a custom docker image to our container registry:

```shell
az acr build -r {the registry} --subscription {the subscription} -t pctasks-sentinel-1-rtc:latest -t pctasks-sentinel-1-rtc:{date}.{count} -f datasets/sentinel-1-rtc/Dockerfile .
```

## Dynamic updates

This collection is updated regularly.

```console
$ pctasks dataset process-items '${{ args.since }}' \
    -d datasets/sentinel-1-rtc/dataset.yaml \
    -c sentinel-1-rtc \
    --workflow-id=sentinel-1-rtc-update \
    --is-update-workflow \
    --upsert
```