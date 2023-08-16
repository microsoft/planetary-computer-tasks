# planetary-computer-tasks dataset: gbif

Global Biodiversity Information Facility

## Building the Docker image

To build and push a custom docker image to our container registry:

```shell
az acr build -r {the registry} --subscription {the subscription} -t pctasks-gbif:latest -t pctasks-gbif:{date}.{count} -f datasets/gbif/Dockerfile .
```

## Update workflow

The update workflow was registered with

```shell
pctasks dataset process-items gbif-update --is-update-workflow --dataset datasets/gbif/dataset.yaml -u
```