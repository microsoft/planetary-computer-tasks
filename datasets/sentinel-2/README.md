# Sentinel-2

## Chunk creation for dynamic ingest

- Using the same chunking split level and options as ETL
    - Listing the `manifest.safe` files
    - Generates about 1000 tasks
- 5-6 hour run-time with a `--since` option and run on the `pctasksteststaging` batch account
- No faster set of chunking options found.

## Docker container

```shell
az acr build -r {the registry} --subscription {the subscription} -t pctasks-sentinel-2:latest -t pctasks-sentinel-2:{date}.{count} -f datasets/sentinel-2/Dockerfile .
```

## Update Workflow

Created with

```
pctasks dataset process-items --is-update-workflow sentinel-2-l2a-update -d datasets/sentinel-2/dataset.yaml
```