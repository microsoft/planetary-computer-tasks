# Colombia Damage 2026

## First-time publishing

Validate the STAC collection first and fix any validation errors:

```bash
pctasks dataset validate-collection datasets/predicted-damage-colombia-2026/collection/template.json
```

Then submit the collection ingestion:

```bash
pctasks dataset ingest-collection -d datasets/predicted-damage-colombia-2026/dataset.yaml -s -a registry pccomponents
```

Take the workflow ID from the output and watch it. It must succeed.

```bash
pctasks runs status $WORKFLOW_ID --watch
curl "https://planetarycomputer.microsoft.com/api/stac/v1/collections/predicted-damage-colombia-2026"
```

## Updating

Simply add `-u` to the command.

```bash
pctasks dataset ingest-collection -d datasets/predicted-damage-colombia-2026/dataset.yaml -u -s -a registry pccomponents
```

## Item ingestion

Assets live under `blob://ai4edataeuwest/ai4good/colombia2026/` and are
organized as `<area>/<YYYY-MM-DD>/`. Chunking lists the `*model-predictions.tif`
files, so each folder produces exactly one STAC item. The sibling GeoPackages
and valid-area mask in that folder become its assets.

Print the workflow without submitting anything:

```bash
pctasks dataset process-items -d datasets/predicted-damage-colombia-2026/dataset.yaml \
  initial-ingest -a registry pccomponents.azurecr.io
```

Try a single item first:

```bash
pctasks dataset process-items -d datasets/predicted-damage-colombia-2026/dataset.yaml \
  test-ingest -a registry pccomponents.azurecr.io --limit 1 --submit
```

Then ingest everything:

```bash
pctasks dataset process-items -d datasets/predicted-damage-colombia-2026/dataset.yaml \
  initial-ingest -a registry pccomponents.azurecr.io --upsert --submit
```

`initial-ingest` and `test-ingest` are chunkset IDs. Use a fresh one whenever
you want to re-list the assets, or pass `-e` to reuse an existing chunkset.

Watch the run and read logs with:

```bash
pctasks runs status $RUN_ID --watch
pctasks runs get run-log $RUN_ID
pctasks runs get task-log $RUN_ID create-splits create-splits -p 0
```

Verify the items landed:

```bash
curl "https://planetarycomputer.microsoft.com/api/stac/v1/collections/predicted-damage-colombia-2026/items?limit=10"
```

## Adding a new area

Upload four files to `colombia2026/<area>/<YYYY-MM-DD>/`:

| File | Becomes |
| --- | --- |
| `*model-predictions.tif` | `visual` |
| `*valid_area_mask.geojson` | `valid-area-mask` |
| `*overture*.gpkg` | `overture-buildings` |
| `*google*.gpkg` or `*hdx*.gpkg` | `google-buildings` |

The folder name sets the item ID, so `pereira/2026-08-12` produces
`pereira-2026-08-12`. Use lowercase, hyphenated area names. Nothing is read
from the file names except the four patterns above.

Then widen `extent.spatial.bbox` in `collection/template.json` if the new area
falls outside it, re-run the collection ingestion with `-u`, and run
`process-items` with a new chunkset ID.

## FAQs

> The workflow failed with "Expected exactly one file matching ...". Why?

Every item needs all four files in its folder, and each pattern must match
exactly one file. Check for a missing upload or two files matching the same
pattern.

> Can I reuse a chunkset ID?

Only with `-e`, which skips re-listing the assets. Newly uploaded areas will
not be picked up that way.

