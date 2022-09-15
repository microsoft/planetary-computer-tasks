# Developing

## Requirements

You must have the following installed in the development environment:

- docker
- python
- go
- [kind](https://kind.sigs.k8s.io/)
- kubectl
- [helm](https://helm.sh/docs/intro/install/)

## Install Python packages

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

You can run `scripts/update` to build the docker images and update dependencies
at any time. Add the `--help` flag to see the available options targeting
subsets of images.


http://localhost:8500

## Bring up development servers

To run the development servers:

```
> scripts/server
```

This will start Azurite, a PgSTAC database, the Azure Functions server, a local executor for testing, a stac-fastapi
to inspect ingest results, and the frontend.

| Service           | URL                          |
| ----------------- | ---------------------------- |
| PC Tasks API      | <http://localhost:8511/runs> |
| PC Tasks Frontend | <http://localhost:8515>      |
| STAC API          | <http://localhost:8513>      |
| STAC Browser      | <http://localhost:8514>      |

You can avoid building or bringing up the STAC API and STAC Browser
servers by using the flag `--no-aux-servers` in `scripts/setup`,
`scripts/update`, and `scripts/server`. This can save on build time
and memory footprint if you are not using those services.

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
