# planetary-computer-tasks dataset: modis

`pctasks` for all MODIS Collections

## Chunking for dynamic ingest

- Asset chunkfile creation with a `--since` argument should take about 10 minutes for each Collection.

## Building the Docker image

To build and push a custom docker image to our container registry:

```shell
az acr build -r {the registry} --subscription {the subscription} -t pctasks-modis:latest -t pctasks-modis:{date}.{count} -f datasets/modis/Dockerfile .
```

Note the force reinstall of `rasterio` in the Dockerfile is necessary for rasterio to read the `.hdf` assets.

## Update workflow

The update workflows were registered with

```shell
ls -1 datasets/modis/collection/ | xargs -I {} bash -c 'echo y | pctasks dataset process-items goes-update --is-update-workflow --dataset datasets/modis/dataset.yaml -u -c {}'
```



## Dynamic Updates

```
ls -1 datasets/modis/collection/ | \
    xargs -I {} pctasks dataset process-items update \
    -c {} \
    --workflow-id {}-update \
    --is-update-workflow \
    --dataset datasets/modis/dataset.yaml \
    --upsert
```