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
ls -1 datasets/modis/collection/ | xargs -I {} pctasks dataset process-items goes-update --is-update-workflow --dataset datasets/modis/dataset.yaml -u -c {}
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

Not using `xargs` here, since we need to lowercase the folder name for the queue

```
pctasks workflow upsert-and-submit datasets/modis/streaming.yaml --arg queue_account_url https://pctasksteststaging.queue.core.windows.net --arg cosmosdb_url https://cdb-pctaskstest-staging.documents.azure.com:443/ --arg registry pccomponentstest.azurecr.io --arg collection_id "modis-09A1-061"    --arg queue_name "modis-09a1-061"

pctasks workflow upsert-and-submit datasets/modis/streaming.yaml --arg queue_account_url https://pctasksteststaging.queue.core.windows.net --arg cosmosdb_url https://cdb-pctaskstest-staging.documents.azure.com:443/ --arg registry pccomponentstest.azurecr.io --arg collection_id "modis-09Q1-061"    --arg queue_name "modis-09q1-061"
pctasks workflow upsert-and-submit datasets/modis/streaming.yaml --arg queue_account_url https://pctasksteststaging.queue.core.windows.net --arg cosmosdb_url https://cdb-pctaskstest-staging.documents.azure.com:443/ --arg registry pccomponentstest.azurecr.io --arg collection_id "modis-10A1-061"    --arg queue_name "modis-10a1-061"
pctasks workflow upsert-and-submit datasets/modis/streaming.yaml --arg queue_account_url https://pctasksteststaging.queue.core.windows.net --arg cosmosdb_url https://cdb-pctaskstest-staging.documents.azure.com:443/ --arg registry pccomponentstest.azurecr.io --arg collection_id "modis-10A2-061"    --arg queue_name "modis-10a2-061"
pctasks workflow upsert-and-submit datasets/modis/streaming.yaml --arg queue_account_url https://pctasksteststaging.queue.core.windows.net --arg cosmosdb_url https://cdb-pctaskstest-staging.documents.azure.com:443/ --arg registry pccomponentstest.azurecr.io --arg collection_id "modis-11A1-061"    --arg queue_name "modis-11a1-061"
pctasks workflow upsert-and-submit datasets/modis/streaming.yaml --arg queue_account_url https://pctasksteststaging.queue.core.windows.net --arg cosmosdb_url https://cdb-pctaskstest-staging.documents.azure.com:443/ --arg registry pccomponentstest.azurecr.io --arg collection_id "modis-11A2-061"    --arg queue_name "modis-11a2-061"
pctasks workflow upsert-and-submit datasets/modis/streaming.yaml --arg queue_account_url https://pctasksteststaging.queue.core.windows.net --arg cosmosdb_url https://cdb-pctaskstest-staging.documents.azure.com:443/ --arg registry pccomponentstest.azurecr.io --arg collection_id "modis-13A1-061"    --arg queue_name "modis-13a1-061"
pctasks workflow upsert-and-submit datasets/modis/streaming.yaml --arg queue_account_url https://pctasksteststaging.queue.core.windows.net --arg cosmosdb_url https://cdb-pctaskstest-staging.documents.azure.com:443/ --arg registry pccomponentstest.azurecr.io --arg collection_id "modis-13Q1-061"    --arg queue_name "modis-13q1-061"
pctasks workflow upsert-and-submit datasets/modis/streaming.yaml --arg queue_account_url https://pctasksteststaging.queue.core.windows.net --arg cosmosdb_url https://cdb-pctaskstest-staging.documents.azure.com:443/ --arg registry pccomponentstest.azurecr.io --arg collection_id "modis-14A1-061"    --arg queue_name "modis-14a1-061"
pctasks workflow upsert-and-submit datasets/modis/streaming.yaml --arg queue_account_url https://pctasksteststaging.queue.core.windows.net --arg cosmosdb_url https://cdb-pctaskstest-staging.documents.azure.com:443/ --arg registry pccomponentstest.azurecr.io --arg collection_id "modis-14A2-061"    --arg queue_name "modis-14a2-061"
pctasks workflow upsert-and-submit datasets/modis/streaming.yaml --arg queue_account_url https://pctasksteststaging.queue.core.windows.net --arg cosmosdb_url https://cdb-pctaskstest-staging.documents.azure.com:443/ --arg registry pccomponentstest.azurecr.io --arg collection_id "modis-15A2H-061"   --arg queue_name "modis-15a2h-061"
pctasks workflow upsert-and-submit datasets/modis/streaming.yaml --arg queue_account_url https://pctasksteststaging.queue.core.windows.net --arg cosmosdb_url https://cdb-pctaskstest-staging.documents.azure.com:443/ --arg registry pccomponentstest.azurecr.io --arg collection_id "modis-15A3H-061"   --arg queue_name "modis-15a3h-061"
pctasks workflow upsert-and-submit datasets/modis/streaming.yaml --arg queue_account_url https://pctasksteststaging.queue.core.windows.net --arg cosmosdb_url https://cdb-pctaskstest-staging.documents.azure.com:443/ --arg registry pccomponentstest.azurecr.io --arg collection_id "modis-16A3GF-061"  --arg queue_name "modis-16a3gf-061"
pctasks workflow upsert-and-submit datasets/modis/streaming.yaml --arg queue_account_url https://pctasksteststaging.queue.core.windows.net --arg cosmosdb_url https://cdb-pctaskstest-staging.documents.azure.com:443/ --arg registry pccomponentstest.azurecr.io --arg collection_id "modis-17A2H-061"   --arg queue_name "modis-17a2h-061"
pctasks workflow upsert-and-submit datasets/modis/streaming.yaml --arg queue_account_url https://pctasksteststaging.queue.core.windows.net --arg cosmosdb_url https://cdb-pctaskstest-staging.documents.azure.com:443/ --arg registry pccomponentstest.azurecr.io --arg collection_id "modis-17A2HGF-061" --arg queue_name "modis-17a2hgf-061"
pctasks workflow upsert-and-submit datasets/modis/streaming.yaml --arg queue_account_url https://pctasksteststaging.queue.core.windows.net --arg cosmosdb_url https://cdb-pctaskstest-staging.documents.azure.com:443/ --arg registry pccomponentstest.azurecr.io --arg collection_id "modis-17A3HGF-061" --arg queue_name "modis-17a3hgf-061"
pctasks workflow upsert-and-submit datasets/modis/streaming.yaml --arg queue_account_url https://pctasksteststaging.queue.core.windows.net --arg cosmosdb_url https://cdb-pctaskstest-staging.documents.azure.com:443/ --arg registry pccomponentstest.azurecr.io --arg collection_id "modis-21A2-061"    --arg queue_name "modis-21a2-061"
pctasks workflow upsert-and-submit datasets/modis/streaming.yaml --arg queue_account_url https://pctasksteststaging.queue.core.windows.net --arg cosmosdb_url https://cdb-pctaskstest-staging.documents.azure.com:443/ --arg registry pccomponentstest.azurecr.io --arg collection_id "modis-43A4-061"    --arg queue_name "modis-43a4-061"
pctasks workflow upsert-and-submit datasets/modis/streaming.yaml --arg queue_account_url https://pctasksteststaging.queue.core.windows.net --arg cosmosdb_url https://cdb-pctaskstest-staging.documents.azure.com:443/ --arg registry pccomponentstest.azurecr.io --arg collection_id "modis-64A1-061"    --arg queue_name "modis-64a1-061"

```