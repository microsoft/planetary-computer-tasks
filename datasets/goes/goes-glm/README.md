# GOES-GLM

This dataset catalogs https://planetarycomputer.microsoft.com/dataset/goes-glm.

## Dynamic updates

The update workflows were generated with the following:

```console
$ pctasks dataset process-items '${{ args.since }}' \
    -d datasets/goes/goes-glm/dataset.yaml \
    -c goes-glm \
    --workflow-id=goes-glm-update \
    --is-update-workflow \
    > datasets/goes/goes-glm/workflows/goes-glm-update.yaml
```

As an optimization, I manually appended `2022` to the `prefix`. That will require updating in the new year. Longer-term pctasks should
optionally do that dynamically from `since`. Likewise for `blue` with a `--workflow-id=goes-glm-update-blue`.

And registered with

```console
$ pctasks workflow create datasets/goes/goes-glm/workflows/goes-glm-update.yaml
```
