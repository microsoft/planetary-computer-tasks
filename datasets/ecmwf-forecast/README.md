# ECMWF Forecast

## Collections

Both collections use `EcmwfCollection`, which reads the resolution from the asset
path. Collection selection is configured in [dataset.yaml](./dataset.yaml):

| Collection | Source resolution | Chunk-storage prefix |
| --- | --- | --- |
| `ecmwf-forecast` | `ifs/0p25/` and legacy `ifs/0p4-beta/` | `ecmwf-etl-data/pctasks/` |
| `ecmwf-forecast-0p1` | `ifs/0p1/` | `ecmwf-etl-data/pctasks-0p1/` |

The filters are disjoint and continue to exclude AIFS and `-opendata` streams.
Specify `-c` / `--collection` when running dataset commands now that there are
multiple collections.

## Chunks

- Asset chunk creation takes 5-10 minutes when passing a `--since {date}` argument.
- There are about 950 `grib2` files generated each day.
- Item creation is fast (the data is not touched), so a single chunk file for daily data is fine — no need to limit `chunk_length`.

## Dockerfile
Build and publish a new container image with:
```shell
tag="20240314.1"
registry="pccomponents"
image="$registry.azurecr.io/pctasks-ecmwf-forecast:$tag"
az acr login -n $registry
docker build -t $image -f datasets/ecmwf-forecast/Dockerfile .
docker push $image
```

Or:

```shell
az acr build -r {the registry} --subscription {the subscription} -t pctasks-ecmwf-forecast:latest -t pctasks-ecmwf-forecast:{date}.{count} -f datasets/ecmwf-forecast/Dockerfile .
```

## Registering the new collection

Before ingesting 0.1-degree items, create the destination collection using
[its template](./collection-0p1/template.json). First preview the workflow:

```shell
pctasks dataset ingest-collection -d datasets/ecmwf-forecast/dataset.yaml -c ecmwf-forecast-0p1 -a registry pccomponents.azurecr.io -a year-prefix ""
```

After reviewing it, repeat with `--submit --confirm` to register the collection.
The new template deliberately does not advertise a GeoParquet export that has
not yet been created.

## Update workflows

Preview both update workflows (omit `--upsert` when previewing):

```shell
pctasks dataset process-items ecmwf-forecast-update --is-update-workflow -d datasets/ecmwf-forecast/dataset.yaml -c ecmwf-forecast -a registry pccomponents.azurecr.io -a year-prefix ""
pctasks dataset process-items ecmwf-forecast-0p1-update --is-update-workflow -d datasets/ecmwf-forecast/dataset.yaml -c ecmwf-forecast-0p1 -a registry pccomponents.azurecr.io -a year-prefix ""
```

Check the generated collection IDs, resolution filters, image tags, and storage
prefixes, then repeat each command with `--upsert`. If the existing workflow was
published with a custom `--workflow-id`, supply that same ID when republishing it.
Configure the update trigger/schedule for the new collection as well; upserting a
workflow alone does not schedule it.

Do not reuse old mixed-resolution chunks with `--use-existing-chunks`: regenerate
them with the new filters. Existing 0.1-degree items in `ecmwf-forecast` are not
moved or deleted by this change. Backfill the new collection from available
source assets, verify it, and plan any cleanup of old items separately.

## Streaming workflow

The [streaming example](./streaming.yaml) takes a `collection_id` argument and
uses a queue with that same name. Run one workflow per collection:

```shell
pctasks workflow upsert-and-submit datasets/ecmwf-forecast/streaming.yaml --arg collection_id ecmwf-forecast --arg queue_account_url https://pctasksteststaging.queue.core.windows.net --arg cosmosdb_url https://cdb-pctaskstest-staging.documents.azure.com:443/ --arg registry pccomponentstest.azurecr.io
pctasks workflow upsert-and-submit datasets/ecmwf-forecast/streaming.yaml --arg collection_id ecmwf-forecast-0p1 --arg queue_account_url https://pctasksteststaging.queue.core.windows.net --arg cosmosdb_url https://cdb-pctaskstest-staging.documents.azure.com:443/ --arg registry pccomponentstest.azurecr.io
```

**Before starting these workflows**, provision both queues and update the
upstream message routing so only `0p25` / `0p4-beta` assets enter `ecmwf-forecast`
and only `0p1` assets enter `ecmwf-forecast-0p1`. Streaming does not apply the
dataset's chunk filters. Reconcile any pending mixed-resolution messages before
restarting the old consumer. These commands do not configure message producers.

## Configuration tests

Run the offline routing and template tests without loading the repository's
service-dependent root fixtures:

```shell
python3 -m pytest --confcutdir=datasets/ecmwf-forecast datasets/ecmwf-forecast/test_configuration.py
```