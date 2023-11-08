# planetary-computer-tasks dataset: nasa-nex-gddp-cmip6

NASA NEX GDDP CMIP6 Dataset

## Building the Docker image

To build and push a custom docker image to our container registry:

```shell
az acr build -r {the registry} --subscription {the subscription} -t pctasks-nasa-nex-gddp-cmip6:latest -t pctasks-nasa-nex-gddp-cmip6:{date}.{count} -f datasets/nasa-nex-gddp-cmip6/Dockerfile .
```

## Static update

This collection is not regularly updated.

```console
$ pctasks dataset process-items \
    -d datasets/nasa-nex-gddp-cmip6/dataset.yaml \
    nasa-nex-gddp-cmip-test
    --arg registry pccomponentstest.azurecr.io \
    --upsert --submit
```

**Notes:**

- Currently uses chunk size of one, because the item creation was timing out with chunksize of 100. However, haven't investigated middle ground.
- Runs in about 10 hours.