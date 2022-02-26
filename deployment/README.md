# Deployment



# TODO: Rewrite from old (below)

This folder contains the code to run a deployment of the ETL in the test infrastructure. It includes a few steps that use Terraform and Helm.

## Deploy script

The logic for the deployment workflow is encapsulated in the [bin/deploy](bin/deploy) script. This should be run from the top level of the repository via `scripts/cideploy` by CI. You can also drop into a console to manually run steps for a dev deployment via

```
scripts/console --deploy
```

or run a dev deployment via

```
scripts/cideploy --dev
```

### Deployment environments

This project is a Planetary Computer Components project, and so does not directly deploy to the Planetary Computer environments. There is however a staging deployment that is published to the 'Planetary Computer Test' Azure subscription through Azure pipelines. This deployment is based on the `deployment/terraform/staging` code.

You can also deploy the staging stack to your own subscription by using the `deployment/terraform/dev` configuration code. To do this, ensure you have created the necessary manual resources described below. That deployment code will use your username to prefix resources; use

```
> export TF_VAR_username=${USER}
```

_Note:_ The username cannot be longer than 7 characters because of the Batch naming convention

or similar to provide the variable to terraform. Or, you will be prompted for the username when you run terraform commands. You are responsible for brining up and down resources, and the terraform state will be stored on your local machine.

### Manual resources

There a few manual resources that need to be created
to run a test deployment in a subscription:

- The database
- A resource group named `pc-test-manual-resources`
- A keyvault named `pc-test-deploy-secrets`
- An ACR, which is named uniquely for a Tenant, for example: `uniquenamecomponentstest`

The database should be a Azure hosted DB service like Flexible Server or Citus Hyperscale. The way ETL accesses the database is via the credentials set in the `pc-test-deploy-secrets` key vault.

The ACR name also needs to be added to the terraform variables, for example:

```
> export TF_VAR_pc_test_resources_acr="uniquenamecomponentstest"
```

These resources are general across several PC deployments.

In addition, some ETL-specific deployment resources need to be created

- A service principal with pull access to that ACR, whose client ID and secret are recorded in the keyvault as `pct-etl-{env}--batch-acr-client-id` and `pct-etl-{env}--batch-acr-client-secret`
- An ETL key vault. This is the key vault that will be pulled from by task containers for credentials like service principal information and database logins while executing in Batch. For extra security, scope the Key Vault to only be accessed by the VNet created in this project.
- A service principal that tasks will use to access Azure resources. The credentials of this service principal are stored in the ETL keyvault.
- A service principal that has access to the ETL key vault. The credentials are injected into the submit container and passed along as command line arguments during the Batch job submission.

#### Credentials used within task containers

- A keyvault names `pct-etl-kv` that holds secrets that will be used inside the task containers
- A service principal that has secret read access to that keyvault, as well as any storage accounts that need to be written to.

All manual resources use the resource group specified in the list.

### Deployment secrets

The terraform uses the keyvault for storing deployment secrets like database passwords. You will need to set all required secrets in the keyvault for terraform to deploy successfully. See [deployment/terraform/resources/keyvault.tf](deployment/terraform/resources/keyvault.tf) for the keys required to have values in the keyvault. If the keys for your environment don't exist in the keyvault, you'll get an error during `terraform plan` with a list of required secrets, e.g.

```
KeyVault Secret "pct-etl-satya--db-admin-login" (KeyVault URI "https://pc-test-deploy-secrets.vault.azure.net/") does not exist
```

Add those keys and values if you have permission, or contact an admin. To do this:

Set `pct-etl-{env}--db-admin-login` with a database admin username, and `pct-etl-{env}--db-admin-password` as the value of the client secret.

## Dev deployment

To deploy your own stack, terraform will run in
the `deployment/terraform/dev` stack. Run `scripts/cideploy --dev` to do this. You'll need the following
environment variables set according with the credential
information for a service principal that has permissions
to deploy to your subscription:

- `subscriptionId`
- `tenantId`
- `servicePrincipalId`
- `servicePrincipalKey`


__Note:__ Remember to bring down your resources after testing with `terraform destroy`!

To do this, drop into the console

```
scripts/console --deploy
```

And

```
cd terraform/dev
terraform init --upgrade
terraform destroy --auto-approve
```
