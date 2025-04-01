# planetary-computer-tasks dataset: sentinel-5p

Sentinel 5 Precursor

## Building the Docker image

To build and push a custom docker image to our container registry:

```shell
az acr build -r {the registry} --subscription {the subscription} -t pctasks-sentinel-5p:latest -t pctasks-sentinel-5p:{date}.{count} -f datasets/sentinel-5p/Dockerfile .
```

## Dynamic updates

This collection is updated regularly.

```console
$ pctasks dataset process-items '${{ args.since }}' \
    -d datasets/sentinel-5p/dataset.yaml \
    -c sentinel-5p-l2-netcdf \
    --workflow-id=sentinel-5p-l2-netcdf-update \
    --is-update-workflow \
    --upsert
```

**Notes:**

- Chunking takes about 20 minutes with a product and year prefix (`year-prefix` argument) and using the `--since` argument
- Item creation for a few days of data and a chunk size of 200 takes about 20 minutes.

## Run ingestion manually

```bash
pctasks dataset process-items -d dataset.yaml test-ingest -a registry pccomponents.azurecr.io --limit 100 --submit --arg year-prefix 2025
or 
pctasks dataset process-items -d dataset.yaml test-ingest -a registry pccomponents.azurecr.io --submit --arg year-prefix 2025
pctasks runs status -w <run id>
```
