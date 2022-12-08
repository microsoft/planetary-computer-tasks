# planetary-computer-tasks dataset: fws-nwi

## Building the Docker image

To build and push a custom docker image to our container registry:

```shell
az acr build -r {the registry} --subscription {the subscription} -t pctasks-fws-nwi:latest -f datasets/fws-nwi/Dockerfile .
```
