# planetary-computer-tasks dataset: sentinel-5p

Sentinel 5 Precursor

## Building the Docker image

To build and push a custom docker image to our container registry:

```shell
az acr build -r {the registry} --subscription {the subscription} -t pctasks-sentinel-5p:latest -f datasets/sentinel-5p/Dockerfile .
```
