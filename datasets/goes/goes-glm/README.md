# GOES-GLM

This dataset catalogs https://planetarycomputer.microsoft.com/dataset/goes-glm.

## Building the Docker image

From the root of the repo, test building the image with `docker build -f datasets/goes/goes-glm/Dockerfile . -t goes-glm`.
Drop into the image with `docker run -it --rm goes-glm /bin/bash`

- To build and push a custom docker image to our container registry:

    ```shell
    az acr build -r {the registry} --subscription {the subscription} -t pctasks-goes-glm:latest -t pctasks-goes-glm:{date}.{count} -f datasets/goes/goes-glm/Dockerfile .
    ```

## Dynamic updates

```shell
pctasks dataset process-items '${{ args.since }}' -a since 2025-03-01T00:00:00+0000 -a registry pccomponents.azurecr.io -a year-prefix 2025 \
    -d datasets/goes/goes-glm/dataset.yaml \
    -c goes-glm \
    --workflow-id goes-glm-update \
    --is-update-workflow \
    --upsert --submit
```

```shell
pctasks dataset process-items '${{ args.since }}' \
    -d datasets/goes/goes-glm/dataset.yaml \
    -c goes-glm \
    --workflow-id goes-glm-update \
    --is-update-workflow \
    --upsert
```