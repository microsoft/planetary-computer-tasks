# NOAA-MRMS-QPE

This dataset handles https://planetarycomputer.microsoft.com/dataset/group/noaa-mrms-qpe

## Dynamic updates

The update workflows were generated with the following:

```
pctasks dataset process-items '${{ args.since }}' \
    -d datasets/noaa-mrms-qpe/dataset.yaml \
    -c noaa-mrms-qpe-1h-pass1 \
    --workflow-id=noaa_mrms_qpe-noaa-mrms-qpe-1h-pass1-process-items-update \
    --is-update-workflow \
    --upsert

pctasks dataset process-items '${{ args.since }}' \
    -d datasets/noaa-mrms-qpe/dataset.yaml \
    -c noaa-mrms-qpe-1h-pass2 \
    --workflow-id=noaa_mrms_qpe-noaa-mrms-qpe-1h-pass2-process-items-update \
    --is-update-workflow \
    --upsert

pctasks dataset process-items '${{ args.since }}' \
    -d datasets/noaa-mrms-qpe/dataset.yaml \
    -c noaa-mrms-qpe-24h-pass2 \
    --workflow-id=noaa_mrms_qpe-noaa-mrms-qpe-24h-pass2-process-items-update \
    --is-update-workflow \
    --upsert
```
