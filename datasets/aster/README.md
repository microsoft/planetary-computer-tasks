# planetary-computer-tasks dataset: aster

For now, this dataset exists only to update existing ASTER items with new geometries, using [stactools's footprint capabilities](https://stactools.readthedocs.io/en/stable/footprint.html).
See [update-geometries.yaml](./update-geometries.yaml) for the workflow.

## Running

To run a test and watch it go:

```shell
pctasks workflow upsert-and-submit datasets/aster/update-geometries.yaml | tee /dev/stderr | xargs pctasks runs status -w
```

### Building the Docker image

The update geometries workflow takes a lot of workers, and if they all hit PyPI at the same time, they can get rate limited.
To avoid that problem, we use a custom image in the workflow.
To build and push a custom docker image to our container registry:

```shell
az acr build -r {the registry} --subscription {the subscription} -t pctasks-aster:latest -f datasets/aster/Dockerfile .
```
