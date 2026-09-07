# planetary-computer-tasks dataset: nasa-nex-gddp-cmip6-netcdf

NASA NEX GDDP CMIP6 Dataset

## Building the Docker image

To build and push a custom docker image to our container registry:

```shell
az acr build -r {the registry} --subscription {the subscription} -t pctasks-nasa-nex-gddp-cmip6-netcdf:latest -t pctasks-nasa-nex-gddp-cmip6-netcdf:{date}.{count} -f datasets/nasa-nex-gddp-cmip6-netcdf/Dockerfile .
```

## Version Information

The upstream provider will occasionally update certain assets in the dataset
(e.g. the `pr` variable will be updated for some models). We want to host just
the latest version of each asset.

The code in `nasa_nex_gddp_cmip6.py` will list files under a prefix and discover
the latest version of each asset. These files are read and passed into the STAC
item creation method.

## Static update

This collection is not regularly updated.

```console
$ pctasks dataset process-items \
    -d datasets/nasa-nex-gddp-cmip6-netcdf/dataset.yaml \
    nasa-nex-gddp-cmip-test
    --arg registry pccommponents.azurecr.io \
    --upsert --submit
```

## Kerchunk Index Files

We have "experimental" Kerchunk index files. We include a
[kerchunk-workflow](./kerchunk-workflow.yaml) for generating these files.


**Notes:**

- Currently uses chunk size of one, because the item creation was timing out with chunksize of 100. However, haven't investigated middle ground.
- Runs in about 10 hours.