# NAIP

## Running

Provide the year (or a regex of years) you want to process.

```shell
$ pctasks dataset process-items --dataset datasets/naip/dataset.yaml test-2023-04-24 --arg year '(2021|2022)'
```

## Docker container

```shell
az acr build -r {the registry} --subscription {the subscription} -t pctasks-naip:latest -f datasets/naip/Dockerfile .
```
