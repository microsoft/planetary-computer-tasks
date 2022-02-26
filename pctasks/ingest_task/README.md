# Planetary Computer Tasks: Ingest

Ingest task for the PCTasks framework. This task handles ingesting STAC data into the PgSTAC database.

## Types of ingests

### STAC Collections

Collections are ingested one at a time by submitting tasks with data containing the Collection JSON.

### STAC Items

There are three separate ways to ingest Items, which optimize for different use cases.

#### Ingesting a single Item

If the task data has a single Item, that Item will be ingested directly into the database.

#### Ingesting an NDJSON file

A message can point to an ndjson file, which will cause all Items in that ndjson file to be ingested in one Task.
The message data looks like:

```javascript
{
    "type": "ndjson",
    "path": "blob://account/container/items.ndjson"
}
```

#### Ingesting a set of NDJSON files

In cases where there's a significant amount of items to ingest, it's fastest to download the ndjsons in parallel and package the
database updates for each ndjson on a single thread. In this case, send a message that is a single column CSV containing
the paths to all NDJSONs:

```javascript
{
    "type": "bulk-ndjson",
    "path": "blob://account/container/paths.csv"
}
```