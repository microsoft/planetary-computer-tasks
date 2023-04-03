# planetary-computer-tasks dataset: io-biodiversity

## Building the Docker image

To build and push a custom docker image to our container registry:

```shell
az acr build -r {the registry} --subscription {the subscription} -t pctasks-io-biodiversity:latest -f datasets/io-biodiversity/Dockerfile .
```
