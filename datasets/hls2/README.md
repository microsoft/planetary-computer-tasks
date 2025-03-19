# Misc notes as Marc created the dataset

## Test local code on dev or prod server

```bash
cd datasets/hls2
pctasks dataset ingest-collection -d dataset.yaml -c hls2-l30 -a registry pccomponents --submit
pctasks runs status <workflow id from output>
<wait for it to succeede>
curl https://planetarycomputer.microsoft.com/api/stac/v1/collections/hls2-l30
```

any future updates, do the command with the -u flag

-c is needed in this case because we have 2 different collections

--limit limits the number of STAC Items being processed

Process (create) Items with:

```bash
pctasks profile list
pctasks profile set openpctest
pctasks dataset process-items -d dataset.yaml -c hls2-l30 test-ingest -a registry pccomponents.azurecr.io --limit 100 --submit
or
pctasks dataset process-items -d dataset.yaml -c hls2-l30 test-ingest -a registry pccomponents.azurecr.io --submit
pctasks dataset process-items -d dataset.yaml -c hls2-s30 test-ingest -a registry pccomponents.azurecr.io --submit
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

```bash

pctasks dataset process-items --is-update-workflow sentinel-2-l2a-update -d datasets/sentinel-2/dataset.yaml -u

```