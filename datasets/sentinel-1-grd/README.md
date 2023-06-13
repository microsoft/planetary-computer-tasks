# planetary-computer-tasks dataset: sentinel-1-grd

Sentinel-1 GRD

## Docker image

To build and push a custom docker image to our container registry:

```shell
az acr build -r {the registry} --subscription {the subscription} -t pctasks-sentinel-1-grd:latest -t pctasks-sentinel-1-grd:{date}.{count} -f datasets/sentinel-1-grd/Dockerfile .
```

## Notes

- Requires `--arg extra-prefix {year}`