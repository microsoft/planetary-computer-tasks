# Landsat C2

The dataset is split into two Collections:

- Level-1 data from the mss sensor: `landsat-c2-l1`
- Level-2 data from the tm, etm+, oli, and tirs sensors: `landsat-c2-l2`

## Chunking for dynamic ingest

Typical scene directory path: `landsat-c2-l2/level-2/standard/oli-tirs/2023/014/020/LC08_L2SP_014020_20230205_20230209_02_T2`

### landsat-c2-l2

Results when using a `--since` argument set 1-2 days in the past:
- If we split to parallelize by year, about half of the years take over an hour to chunk (more, since I canceled the job after an hour).
- If we pass in a `year-prefix` arg and split by the landsat WRS grid row (one directory below the year), we spawn around 450 tasks (one for each row of the landsat WRS grid), but are able to create chunks in about 10 minutes.

  ```shell
  pctasks dataset create-chunks -d datasets/landsat/dataset.yaml -c landsat-c2-l2 {CHUNKSET_ID} --since {date} --submit --arg year-prefix 2023 --arg registry pccomponentstest.azurecr.io
  ```

### landsat-c2-l1

- Not tested since this data is no longer being produced.

## Building the Docker image

To build and push a custom docker image to our container registry:

```shell
az acr build -r {the registry} --subscription {the subscription} -t
pctasks-landsat:latest -t pctasks-landsat:{date}.{count} -f datasets/landsat/Dockerfile .
```
