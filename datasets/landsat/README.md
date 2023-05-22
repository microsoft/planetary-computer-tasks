# Landsat C2

The dataset is split into two Collections:

- Level-1 data from the mss sensor: `landsat-c2-l1`
- Level-2 data from the tm, etm+, oli, and tiirs sensors: `landsat-c2-l2`

## Building the Docker image

To build and push a custom docker image to our container registry:

```shell
az acr build -r {the registry} --subscription {the subscription} -t
pctasks-landsat:latest -f datasets/landsat/Dockerfile .
```
