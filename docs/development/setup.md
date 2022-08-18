# Setting up the development environment

## Requirements

You must have the following installed in the development environment:

- docker
- python
- go
- [kind](https://kind.sigs.k8s.io/)
- kubectl
- [helm](https://helm.sh/docs/intro/install/)

## Install packages

Run

```
> scripts/install
```

to install the packages into a virtualenv (note: activate the virtualenv beforehand.) You should run this even if you are only doing docker development, otherwise the python eggs installed into the container will be overridden by volume mounts.

## Set up development environment

Run

```
> scripts/setup
```

To build set up the development cluster, build docker images,
and set up test data.

You can run `scripts/update` to build the docker images at any time.


http://localhost:8500

## Bring up development servers

To run the development servers:

```
> scripts/server
```

This will start Azurite, a PgSTAC database, the Azure Functions server, a local executor for testing, and a stac-fastapi
to inspect ingest results.

You can access the STAC API at http://localhost:8510/stac and a stac-browser of the API at http://localhost:8510/browser

## Bring up the development Kind cluster

If you are using the development cluster, use the `scripts/cluster` script to manage the cluster:

```
# Create cluster, install Helm charts, publish relevant docker images to local registry:
scripts/cluster setup
# Update the helm charts and images
scripts/cluster update
# Get an Argo token that can be used to log into the Argo UI
scripts/cluster argo-token
# Destroys and recreates the cluster
scripts/cluster recreate
# Deletes the cluster
scripts/cluster delete
```

Clusters are ephemeral, and can take up significant resources; it is fine to run `scripts/cluster delete` and `scripts/cluster create` as needed.

## Setting up local secrets

PCTasks uses a docker container run via `docker-compose`, brought up by `scripts/server`, to mock the functionality of KeyVault for fetching secrets.
It will return any secret that is contained in the `dev-secrets.yaml` file in the root directory of the repository.

To create secrets, copy `dev-secrets.template.yaml` to `dev-secrets.yaml`, and fill in any key/value pairs
you need for secrets, e.g. the `tenant-id`, `client-id`, and `client-secret` for our Azure service principal.

## Testing

Run

```
> scripts/test
```

to test. You can also run `scripts/format` to format code. Use `--help` to see options on any script.

### Kubernetes config

You can export a kubeconfig for `kubectl`

```
> kind export kubeconfig --name kind-pctasks
```

## Argo UI

Once the kind cluster is up, you can view the Argo UI by visiting http://localhost:8500/argo.
You'll need to use your ARGO_TOKEN to log in, which you can
find using `scripts/cluster argo-token`
