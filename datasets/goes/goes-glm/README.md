# GOES-GLM

This dataset catalogs https://planetarycomputer.microsoft.com/dataset/goes-glm.

## Dynamic updates

```
$ pctasks dataset process-items '${{ args.since }}' \
    -d datasets/goes/goes-glm/dataset.yaml \
    -c goes-glm \
    --workflow-id goes-glm-update \
    --is-update-workflow \
    --upsert
```