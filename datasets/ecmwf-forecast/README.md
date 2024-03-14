# ECMWF Forecast

## Chunks

- Asset chunk creation takes 5-10 minutes when passing a `--since {date}` argument.
- There are about 950 `grib2` files generated each day.
- Item creation is fast (the data is not touched), so a single chunk file for daily data is fine — no need to limit `chunk_length`.

## Dockerfile

```shell
az acr build -r {the registry} --subscription {the subscription} -t pctasks-ecmwf-forecast:latest -t pctasks-ecmwf-forecast:{date}.{count} -f datasets/ecmwf-forecast/Dockerfile .
```

## Update workflow

The update workflow was registered with

```shell
pctasks dataset process-items ecmwf-forecast-update --is-update-workflow --dataset datasets/ecmwf-forecast/dataset.yaml -u
```

## Streaming workflow


```shell
pctasks workflow upsert-and-submit datasets/ecmwf-forecast/streaming.yaml --arg queue_account_url https://pctasksteststaging.queue.core.windows.net --arg cosmosdb_url https://cdb-pctaskstest-staging.documents.azure.com:443/ --arg registry pccomponentstest.azurecr.io
```