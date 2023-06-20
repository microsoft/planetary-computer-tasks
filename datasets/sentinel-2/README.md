# Sentinel-2

## Chunk creation for dynamic ingest

TLDR: Not yet successful in generating a chunking scheme for dynamic ingest

- The `--since` argument does not work when listing folders, so listing all the `.SAFE` directories (as was done in ETL) is not an option.
- Searching for all `manifest.safe` files with a splits depth of 2 spawns almost 1000 tasks. But still takes well over an hour to generate chunks with the `--since` argument, and we run into the problem of the SAS signature timing out.
    - Is it possible that we are getting throttled with all these blob info requests?
- IIUC, the only action that will prevent examining all the blobs is prefixing. 
- IIRC, listing the SAFE directories was much faster than searching for `manifest.safe`

## Docker container

```shell
az acr build -r {the registry} --subscription {the subscription} -t pctasks-sentinel-2:latest -t pctasks-sentinel-2:{date}.{count} -f datasets/sentinel-2/Dockerfile .
```

## ToDo

1. Switch from using a `.SAFE` directory as the input `asset_uri` to a `manifest.safe` xml file as the input `asset_uri`. 
    - Still undecided if we will list `.SAFE` directories or `manifest.safe` xml files (that are in the `.SAFE` directories)?