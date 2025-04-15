# HLS v2

The Sentinel and Landsat portions of this dataset are in two collections: `hls2-l30` and `hls2-s30`.

All management operations must be repeated for both collections to maintain parity.

## Collection Publish

```bash
cd datasets/hls2
pctasks dataset ingest-collection -d dataset.yaml -c hls2-l30 -a registry pccomponents --submit
pctasks dataset ingest-collection -d dataset.yaml -c hls2-s30 -a registry pccomponents --submit
pctasks runs status <workflow id from output>
<wait for it to succeede>
curl https://planetarycomputer.microsoft.com/api/stac/v1/collections/hls2-l30
curl https://planetarycomputer.microsoft.com/api/stac/v1/collections/hls2-s30
```

Notes:

- any future updates, do the command with the `-u` flag for "upsert"
- `-c` is needed in this case because we have 2 different collections in a single `dataset.yaml`.
- `--limit` limits the number of STAC Items being processed

## Ingestion Workflow Publish

Publish the ingestion update workflows with:

```bash
pctasks dataset process-items -d dataset.yaml -c hls2-s30 initial-ingest -a registry pccomponents.azurecr.io --is-update-workflow --workflow-id hls2-s30-update --upsert
pctasks dataset process-items -d dataset.yaml -c hls2-l30 initial-ingest -a registry pccomponents.azurecr.io --is-update-workflow --workflow-id hls2-l30-update --upsert
```

It's important to match the `--workflow-id` with the ID used by the cron jobs!

Once this is done, you only need to run it again if you change code in `hls2.py` or PCTasks code itself.
Under normal operations, the cron jobs will take care of submitting the update workflow.

## Manually Process Items

```bash
pctasks dataset process-items -d dataset.yaml -c hls2-l30 test-ingest -a registry pccomponents.azurecr.io --limit 100 --submit

# or do the whole thing with
pctasks dataset process-items -d dataset.yaml -c hls2-l30 initial-ingest -a registry pccomponents.azurecr.io --upsert --submit 
pctasks dataset process-items -d dataset.yaml -c hls2-s30 initial-ingest -a registry pccomponents.azurecr.io --upsert --submit
```

The last one was left running overnight to ingest all currently onboarded items around April 08, 2025.

or for test-

```bash
pctasks profile list
pctasks profile set openpctest
pctasks dataset process-items -d dataset.yaml -c hls2-l30 test-ingest -a registry pccomponentstest.azurecr.io --submit
pctasks dataset process-items -d dataset.yaml -c hls2-s30 test-ingest -a registry pccomponentstest.azurecr.io --submit
pctasks runs status <workflow id from output>
pctasks runs get run-log <workflow id from output>
pctasks runs get task-log <workflow id from output> create-splits create-splits -p 0
curl https://planetarycomputer.microsoft.com/api/stac/v1/collections/hls2-l30/items
```

To get the workflow to work with cron, use:

```bash
pctasks workflow update datasets/workflows/stac-geoparquet.yaml
```

within cronjob-
"workflow_id": "hls2-s30-update"
"workflow_id": "hls2-l30-update"

## Publishing Collection Configurations

You will need access to the `mspc` CLI, then you may run:

```shell
repo_root=$(git rev-parse --show-toplevel)
environment=test # or green/blue depending on what is active

mspc collections render-configs publish $environment $repo_root hls2-l30
mspc collections render-configs publish $environment $repo_root hls2-s30
```

You can also update monthly mosaics in the collection configuration with:

```shell
mspc collections render-configs update-monthly-mosaics $repo_root hls2-l30 2023-03-01 2025-04-01
mspc collections render-configs update-monthly-mosaics $repo_root hls2-s30 2023-03-01 2025-04-01
```
