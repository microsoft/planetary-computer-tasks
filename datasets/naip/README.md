# NAIP

## Collection Metadata Update

Run this if you need to update the collection STAC item without ingesting asset items.

```shell
pctasks dataset ingest-collection -d datasets/naip/dataset.yaml --submit -a registry pccomponents -arg year '2023'
```

## Running

Provide the year (or a regex of years) you want to process.

```shell
pctasks dataset process-items --dataset datasets/naip/dataset.yaml my-chunkset-id --arg year '(2021|2022)' --arg registry pccomponents.azurecr.io --submit
```

## Docker container

```shell
az acr build -r {the registry} --subscription {the subscription} -t pctasks-naip:latest -f datasets/naip/Dockerfile .
```

## Test

The Azure credentials of the user running the tests will be used.
If found, [environment variables](https://github.com/Azure/azure-sdk-for-go/wiki/Set-up-Your-Environment-for-Authentication)
for service principal authentication will be used.
If the tests are failing due to storage authorization issues, make sure either you or your service principal has access to the storage account.