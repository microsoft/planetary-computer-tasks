# planetary-computer-tasks dataset: sentinel-1-grd

## Chunking for dynamic ingest

- Requires an extra `--arg year-prefix {year}` argument when running `pctasks dataset create-chunks` or `pctasks dataset process-items` commands.
- Asset chunkfile creation takes about 5 minutes.
- Item creation takes about 5 minutes for ~1 day of data.

## Docker image

To build and push a custom docker image to our container registry:

```shell
az acr build -r {the registry} --subscription {the subscription} -t pctasks-sentinel-1-grd:latest -t pctasks-sentinel-1-grd:{date}.{count} -f datasets/sentinel-1-grd/Dockerfile .
```
