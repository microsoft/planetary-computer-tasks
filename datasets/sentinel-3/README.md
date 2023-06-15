# Sentinel-3

## Dataset structure

This dataset has many different products. We create one STAC collection per product. The collections are under the `collection` folder.

```
collection/sentinel-3-olci-lfr-l2-netcdf
collection/sentinel-3-olci-wfr-l2-netcdf
collection/sentinel-3-slstr-frp-l2-netcdf
collection/sentinel-3-slstr-lst-l2-netcdf
collection/sentinel-3-slstr-wst-l2-netcdf
collection/sentinel-3-sral-lan-l2-netcdf
collection/sentinel-3-sral-wat-l2-netcdf
collection/sentinel-3-synergy-aod-l2-netcdf
collection/sentinel-3-synergy-syn-l2-netcdf
collection/sentinel-3-synergy-v10-l2-netcdf
collection/sentinel-3-synergy-vg1-l2-netcdf
collection/sentinel-3-synergy-vgp-l2-netcdf
```

## Tests

The `datasets/sentinel-3/tests` directory contains some tests. Run those with


```
$ PYTHONPATH=datasets/sentinel-3 python -m pytest datasets/sentinel-3/tests/
```

## Dynamic updates

```console
$ ls datasets/sentinel-3/collection/ | xargs -I {}  \
    pctasks dataset process-items '${{ args.since }}' \
        -d datasets/sentinel-3/update.yaml \
        -c {} \
        --workflow-id={}-update \
        --is-update-workflow \
        --upsert
```

**Notes:**

- Takes about 45 minutes to chunk and create items for all collections using the test batch account

## Docker container

```shell
az acr build -r {the registry} --subscription {the subscription} -t pctasks-sentinel-3:latest -t pctasks-sentinel-3:{date}.{count} -f datasets/sentinel-3/Dockerfile .
```