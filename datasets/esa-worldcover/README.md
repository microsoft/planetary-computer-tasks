# planetary-computer-tasks dataset: esa-worldcover

## Building the Docker image

To build and push a custom docker image to our container registry:

```shell
az acr build -r {the registry} --subscription {the subscription} -t pctasks-esa-worldcover:latest -f datasets/esa-worldcover/Dockerfile .
```
