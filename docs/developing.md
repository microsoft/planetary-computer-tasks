# Developing

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
to inspect ingest results. You can access the STAC API at http://localhost:8089/

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

You can view the argo UI by running

```
> kubectl -n argo port-forward deployment/argo-workflow-server 2746:2746
```

and visiting https://localhost:2746
