## Deploying PCTasks

PCTasks deploys using Terraform for infrastructure, Helm for managing helm charts in the AKS cluster, and Azure Function Core Tools for
deploying Azure Functions. The steps to deploy are encapsulated in the `deployment/bin/deploy` script. All deployment operations take
place in the `deploy` service container run through `scripts/console --deploy`, which runs a console in the deploy service container managed
by `deploy/docker-compose.yaml`.

## Required resources

There are resources that PCTasks depends on that are not deployed itself, and need to be managed out-of-band. This can be done by creating
the resources manually through the Azure Portal or through separate terraform processes.

### Deployment Service principal

You'll need a service principal that has sufficient permissions to deploy Azure resources, including creating resource groups and assigning IAM roles.

The service principal information fed to the deployment container through the following environment vars on the host:
- AZURE_SUBSCRIPTION_ID
- AZURE_TENANT_ID
- AZURE_CLIENT_ID
- AZURE_CLIENT_SECRET

### PgSTAC Database

The PgSTAC database information is written into the PCTasks key vault as a secret that is available to workflows through `${{ secrets.pgstac-connection-string }}`.

### Deploy secrets KeyVault

The deploy secrets keyvault holds keys for terraform to read. The keyvault must contain a secret that holds the terraform values file that is used to specify values for terraform variables, described below.

### Terraform Variables

A terraform variables file is stored in the deployment keyvault, which is fetched and applied to the deployment of a specific stack in the terraform stage. The keyvault secret that is fetched depends on the `env.sh` file stored in the stack's terraform directory. For example,
in deployment/terraform/staging, the env.sh reads:

```
#!/bin/bash

export DEPLOY_SECRETS_KV=pc-test-deploy-secrets
export DEPLOY_SECRETS_KV_SECRET=pctasks-test-tfvars-staging
```

This means that the tfvars file to apply to this terraform deploy is in the deploy secrets keyvault named `pc-test-deploy-secrets` under the secret name `pctasks-test-tfvars-staging`.

When creating a new tfvars, use the `values.tfvars.template` in teh `deployment/terraform/resources` directory and fill out all the information. Then you must use the Azure CLI to write the tfvars into keyvault - writing through the portal will strip newlines and will not work.  You can use the `deployment/bin/write_tfvars` script to write a tfvars file to a keyvault secret.

The tfvars template file has documentation on each of the variables that need to be supplied.

Also, you can use the `--skip-fetch-tf-vars` option to `bin/deploy` to skip fetching the terraform values from keyvault, which requires that the `values.tfvars` file be at the proper location in the stack terraform directory.

### Roles

The service principal specified by the `task_acr_sp_object_id` variable must have `AcrPull` permissions on the ACR specified by the `task_acr_name` variable.

## Terraform structure

The terraform is divided into a `resources` folder, which holds all the definitions of resources that are used across environments, and a set of environment stacks like `dev` and `staging`.

The `dev` stack is used to bring up an entire stack of pctasks for personal development. The terraform backend used is local to the users machine. The stack resources will be named according to the `$USER` environment variable.

The `staging` stack is deployed via CI/CD to the sandboxed Planetary Computer Test subscription. Only CI/CD and administrators should run deployment against this stack.

## Running deploy

To run deploy, ensure your deployment service principal environment variables are set and drop into a deployment console with

```
> scripts/console --deploy
```

Then run the deploy script for your stack, e.g.

```
> bin/deploy -t terraform/dev
```
