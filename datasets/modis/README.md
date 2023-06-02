# planetary-computer-tasks dataset: modis

`pctasks` for all MODIS collections

## Building the Docker image

To build and push a custom docker image to our container registry:

```shell
az acr build -r {the registry} --subscription {the subscription} -t pctasks-modis:latest -f datasets/modis/Dockerfile .
```

Note the force reinstall of `rasterio` in the Dockerfile is necessary for rasterio to read the `.hdf` assets.