# NOAA Climate Normals

### Building the Docker image

```shell
az acr build -r $REGISTRY --subscription $SUBSCRIPTION -t pctasks-noaa-climate-normals:latest -f datasets/noaa-climate-normals/Dockerfile .
```
