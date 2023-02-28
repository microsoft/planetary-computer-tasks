# Fix LCMAP Item Asset class lists

Downloads the Item ndjsons from blob storage, removes the land cover change classes from the primary (lcpri) and secondary (lcsec) land cover Assets in each Item, uploades ndjsons containing the corrected Items back to blob storage.

## Running

Edit the `incorrect_chunkset_uri` and `corrected_chunkset_uri` arguments to operate on either CONUS or Hawaii data. Then run:

```shell
pctasks workflow upsert-and-submit datasets/usgs-lcmap/fix-item-classes/fix_items.yaml
```
