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

### Testing (creates a new workflow, does not affect production)

To create or update a test workflow:

```shell
pctasks dataset process-items sentinel-2-l2a-update --is-update-workflow -d datasets/sentinel-2/dataset.yaml -u
```

To submit the test workflow:

```shell
pctasks workflow submit sentinel-2-kn1-sentinel-2-l2a-process-items \
    -a registry pccomponents.azurecr.io \
    -a since "2026-01-16T08:30:00Z"
```

### Production

> ⚠️ **Warning**: The following command will update the production workflow. Only run this if you intend to deploy changes to production.

To update the production workflow:

```shell
pctasks dataset process-items sentinel-2-l2a-update \
    --is-update-workflow \
    --workflow-id sentinel-2-sentinel-2-l2a-update \
    -d datasets/sentinel-2/dataset.yaml \
    -u
```

**Parameters:**

- `sentinel-2-l2a-update` - The chunkset ID for this workflow
- `--is-update-workflow` - Creates an update workflow with `since` as a runtime argument
- `--workflow-id` - Specifies the exact workflow ID to upsert (required for production)
- `-d` - Path to the dataset configuration file
- `-u` - Upsert the workflow through the API

```bash
pctasks dataset process-items --is-update-workflow sentinel-2-l2a-update -d datasets/sentinel-2/dataset.yaml -u
```

## Submit ingestion jobs on demand

```bash
pctasks dataset process-items \
    --is-update-workflow sentinel-2-l2a-update \
    -d datasets/sentinel-2/dataset.yaml -u --submit \
    -a registry pccomponents.azurecr.io \
    -a since "2025-06-16T00:00:00Z"
```
