# CONUS404

## First-time publishing
First you need to validate the STAC collection with `pctasks dataset validate-collection [path-to-template.json]`, fix any validation errors.

Then submit the collection ingestion with `pctasks dataset ingest-collection -d datasets/conus404/dataset.yaml -s -a registry pccomponents`

Get the workflow ID and then watch it with: `pctasks runs status $WORKFLOW_ID --watch`.
It must succeed.

Verify that it was successful with `curl "https://planetarycomputer.microsoft.com/api/stac/v1/collections/conus404"`

## Updating
Simply add `-u` to the command.
`pctasks dataset ingest-collection -d datasets/conus404/dataset.yaml -u -s -a registry pccomponents`