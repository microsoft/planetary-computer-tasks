# Planetary Computer Tasks (pctasks)

`pctasks` runs scalable workflows on Azure. It's used as a reactive ETL system for getting data into
the Planetary Computer STAC.

## Developing

### Requirements

You must have the following installed in the development environment:

- docker
- python
- go
- [kind](https://kind.sigs.k8s.io/)
- kubectl
- [helm](https://helm.sh/docs/intro/install/)

### Install packages

Run

```
> scripts/install
```

to install the packages into a virtualenv (note: activate the virtualenv beforehand.) You should run this even if you are only doing docker development, otherwise the python eggs installed into the container will be overridden by volume mounts.

### Set up development environment

Run

```
> scripts/setup
```

To build set up the development cluster, build docker images,
and set up test data.

You can run `scripts/update` to build the docker images at any time.

### Bring up development servers

To run the development servers:

```
> scripts/server
```

This will start Azurite, a PgSTAC database, the Azure Functions server, a local executor for testing, and a stac-fastapi
to inspect ingest results. You can access the STAC API at http://localhost:8089/

### Testing

Run

```
> scripts/test
```

to test. You can also run `scripts/format` to format code. Use `--help` to see options on any script.

### Argo UI

You can view the argo UI by running

```
> kubectl -n argo port-forward deployment/argo-server 2746:2746
```

and visiting https://localhost:2746


## Contributing

This project welcomes contributions and suggestions.  Most contributions require you to agree to a
Contributor License Agreement (CLA) declaring that you have the right to, and actually do, grant us
the rights to use your contribution. For details, visit https://cla.opensource.microsoft.com.

When you submit a pull request, a CLA bot will automatically determine whether you need to provide
a CLA and decorate the PR appropriately (e.g., status check, comment). Simply follow the instructions
provided by the bot. You will only need to do this once across all repos using our CLA.

This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/).
For more information see the [Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/) or
contact [opencode@microsoft.com](mailto:opencode@microsoft.com) with any additional questions or comments.

## Trademarks

This project may contain trademarks or logos for projects, products, or services. Authorized use of Microsoft
trademarks or logos is subject to and must follow
[Microsoft's Trademark & Brand Guidelines](https://www.microsoft.com/en-us/legal/intellectualproperty/trademarks/usage/general).
Use of Microsoft trademarks or logos in modified versions of this project must not cause confusion or imply Microsoft sponsorship.
Any use of third-party trademarks or logos are subject to those third-party's policies.
