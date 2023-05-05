# planetary-computer-tasks dataset: sentinel-5p

Sentinel 5 Precursor

## Building the Docker image

To build and push a custom docker image to our container registry:

```shell
az acr build -r {the registry} --subscription {the subscription} -t pctasks-sentinel-5p:latest -f datasets/sentinel-5p/Dockerfile .
```

### Dynamic updates

This collection is updated regularly.

```console
$ pctasks dataset process-items '${{ args.since }}' \
    -d datasets/sentinel-5p/update.yaml \
    -c sentinel-5p-l2-netcdf \
    --workflow-id=sentinel-5p-l2-netcdf-update \
    --is-update-workflow \
    --upsert
```