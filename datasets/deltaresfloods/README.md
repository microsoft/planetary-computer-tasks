# deltaresfloods PC Tasks

PCTasks code for ingesting deltaresfloods data into the Planetary Computer.
These STAC items JSONs are stored as blobs in the `deltaresfloodssa` storage account under the `floods-stac` container.
You can mount them locally and make modifications before re-ingesting them into the STAC database.

## Item Updates
After fixing items in the `deltaresfloodssa/floods-stac` container, you may run to reingest them:

```bash
pctasks dataset process-items xarray-access-fix \
    -a since "2024-11-17T00:00:00Z" \
    --dataset datasets/deltaresfloods/dataset.yaml \
    --is-update-workflow --upsert --submit
```

Set since to a date strictly before you modified the STAC items in storage.
For example, if you modified items on December 4, set the since to be any date before December 4.
`since` must be a full ISO8061 datetime.