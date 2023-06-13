# Sentinel-2

## Docker container

```shell
az acr build -r {the registry} --subscription {the subscription} -t pctasks-sentinel-2:latest -t pctasks-sentinel-2:{date}.{count} -f datasets/sentinel-2/Dockerfile .
```
