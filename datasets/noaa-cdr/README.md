# NOAA Climate Data Records (CDR)

### Dynamic updates

`noaa-cdr-sea-surface-temperature-optimum-interpolation` is updated daily.

```console
$ pctasks dataset process-items '${{ args.since }}' \
    -d datasets/noaa-cdr/update.yaml \
    -c noaa-cdr-sea-surface-temperature-optimum-interpolation \
    --workflow-id=noaa-cdr-sea-surface-temperature-optimum-interpolation-update \
    --is-update-workflow \
    --upsert
```