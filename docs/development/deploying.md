# Deploying PCTasks

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

### PC Tasks KeyVault

The PCTasks keyvault for the should be manually created prior to running terraform. Set the KeyVault name and resource group
`pctasks_test_kv` and `pctasks_test_kv_resource_group_name` variables. Note that in the `staging` environment, this manually created resources is in the resource group managed by terraform, but is not itself managed.

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

__Note:__ If you are using the `terraform/dev` stack, which stores its terraform state locally, a `values.tfvars` will not be pulled from the keyvault. You need to create the `values.tfvars` based on the template and copy it into the `terraform/dev` folder manually.

### Azure AD App Registrations

This PC Tasks API and frontend use Azure AD App Registrations to authenticate
users and provide authorization scopes. These applications cannot be
automatically created via the existing terraform deployment code, and instead
must be created manually using the Application Manifest templates located in the
`deployment/manual` directory. Read more about the [Manifest file
schema](https://docs.microsoft.com/en-us/azure/active-directory/develop/reference-app-manifest),
and [using Azure AD to protect API
resources](https://docs.microsoft.com/en-us/azure/active-directory/develop/scenario-protected-web-api-overview).

The steps to create Azure AD App Registrations for use with PCTasks are:

1. Create a new Azure AD App Registration for the PC Tasks API backend app ("the backend app")
2. Create a new Azure AD App Registration for the PC Tasks API frontend app ("the frontend app")
3. Extract values from the initial registrations and merge them into the corresponding app registration manifest template files.
4. In the Azure portal, update the app registrations with the new manifest data.
5. Update the deployment secrets with the new app registration ids.

#### Create new app registrations

Go to the [Azure portal](https://portal.azure.com) and create a new app registration for the backend app:

- Give it a description name that includes the environment it targets, e.g., `pctasks-production-backend-app`.
- Keep the remaining defaults, these values will be set by updating the application manifest later.
- Make a note of the Application ID value for later.

Create a second app registration for the frontend app:

- Give it a description name that includes the environment it targets, e.g., `pctasks-production-frontend-app`.
- Make a note of the Application ID value for later.

#### Merge app registration values into manifest files templates

You'll need to take 4 values from newly created app registrations and merge them into the corresponding app registration manifest template files. Do this for **both** the backend and frontend manifest templates.

| Manifest key name | Template marker               |
|-------------------|-------------------------------|
| `id`              | `{{ application_system_id }}` |
| `appId`           | `{{ application_id }}`        |
| `name`            | `{{ application_name }}`      |
| `createdDateTime` | `{{ created_date_time }}`     |

##### Update backend app manifest values

Updating the manifest file itself is a two-step process because it contains
self-referencing values. First, update the backend app manifest file to include
new values:

| Manifest key name                    | Template marker                     | Value                                                  |
|--------------------------------------|-------------------------------------|--------------------------------------------------------|
| `identifierUris`                     | `{{ application_identifier_uris }}` | List of single value, `api://{{ backend_app_id }}/`    |
| `preAuthorizedApplications[0].appId` | `{{ frontend_app_id }}`             | The Application ID of the frontend app created earlier |

Then, go to the Azure portal and update the backend app registration with the new manifest values:

- Click the "Manifest" link under the "Manage" heading
- Replace the existing manifest file with the fully templated new manifest file
- **Temporarily remove the value for `preAuthorizedApplications`**. Cut the value of the list so it's just an empty array (`[]`). We can't reference the permission ids that are also being created from the manifest file.
- Click save
- Paste back the preAuthorizedApplications value
- Click save

##### Update frontend app manifest values

First, update the frontend app manifest file to include new values:

| Manifest key name                         | Template marker             | Value                                                                                                          |
|-------------------------------------------|-----------------------------|----------------------------------------------------------------------------------------------------------------|
| `replyUrlsWithType[1].url`                | `website_auth_callback_url` | The URL of the website this app registration represents, or a placeholder value if the app is not deployed yet |
| `requiredResourceAccess[1].resourceAppId` | `{{ backend_app_id }}`      | The Application ID of the backend app created earlier                                                          |

Then, go to the Azure portal and update the frontend app registration with the new manifest values:

- Click the "Manifest" link under the "Manage" heading
- Replace the existing manifest file with the fully templated new manifest file
- Click save

The applications are now configured. If structural changes are made to either in the portal, be sure to sync those changes with the template files in this repository.

#### Update deployment secrets

Update the deployment secrets with the new app registration ids:

- `backend_api_app_id_secret_name`: Update the deploy secret referenced by this tf variable to the new backend app registration id. This will allow the APIM policy to access it as a named value and verify that the correct audience claim is present in generated access tokens.

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
