data "azurerm_cosmosdb_account" "pctasks" {
  name                = var.cosmosdb_account_name
  resource_group_name = var.cosmosdb_resource_group
}

# Define the CosmosDB database, containers, stored procedures, triggers, and UDFS
# This MUST be kept in sync with the scripts contained in deployement/cosmosdb/scripts
# and with the python code in pctasks.core.cosmos.containers

resource "azurerm_cosmosdb_sql_database" "pctasks" {
  name                = "pctasks"
  resource_group_name = data.azurerm_cosmosdb_account.pctasks.resource_group_name
  account_name        = data.azurerm_cosmosdb_account.pctasks.name
}

## Workflows

resource "azurerm_cosmosdb_sql_container" "workflows" {
  name                  = "workflows"
  resource_group_name   = data.azurerm_cosmosdb_account.pctasks.resource_group_name
  account_name          = data.azurerm_cosmosdb_account.pctasks.name
  database_name         = azurerm_cosmosdb_sql_database.pctasks.name
  partition_key_path    = "/workflow_id"
}

resource "azurerm_cosmosdb_sql_trigger" "post-all-workflows" {
  name         = "post-all-workflows"
  container_id = azurerm_cosmosdb_sql_container.workflows.id
  body         = file("${path.module}/../../cosmosdb/scripts/triggers/workflows/post-all-workflows.js")
  operation    = "All"
  type         = "Post"
}

## Workflow Runs

resource "azurerm_cosmosdb_sql_container" "workflowruns" {
  name                  = "workflow-runs"
  resource_group_name   = data.azurerm_cosmosdb_account.pctasks.resource_group_name
  account_name          = data.azurerm_cosmosdb_account.pctasks.name
  database_name         = azurerm_cosmosdb_sql_database.pctasks.name
  partition_key_path    = "/run_id"
}

resource "azurerm_cosmosdb_sql_trigger" "post-all-workflowruns" {
  name         = "post-all-workflowruns"
  container_id = azurerm_cosmosdb_sql_container.workflowruns.id
  body         = file("${path.module}/../../cosmosdb/scripts/triggers/workflow-runs/post-all-workflowruns.js")
  operation    = "All"
  type         = "Post"
}

resource "azurerm_cosmosdb_sql_stored_procedure" "bulkput-workflowruns" {
  name         = "bulkput-workflowruns"
  resource_group_name = data.azurerm_cosmosdb_account.pctasks.resource_group_name
  account_name        = data.azurerm_cosmosdb_account.pctasks.name
  database_name       = azurerm_cosmosdb_sql_database.pctasks.name
  container_name      = azurerm_cosmosdb_sql_container.workflowruns.name

  body         = file("${path.module}/../../cosmosdb/scripts/stored_procs/workflow-runs/bulkput-workflowruns.js")
}

## Records

resource "azurerm_cosmosdb_sql_container" "records" {
  name                  = "records"
  resource_group_name   = data.azurerm_cosmosdb_account.pctasks.resource_group_name
  account_name          = data.azurerm_cosmosdb_account.pctasks.name
  database_name         = azurerm_cosmosdb_sql_database.pctasks.name
  partition_key_path    = "/type"
  partition_key_version = 1
}

## Leases (for change feed processing)

resource "azurerm_cosmosdb_sql_container" "leases" {
  name                  = "leases"
  resource_group_name   = data.azurerm_cosmosdb_account.pctasks.resource_group_name
  account_name          = data.azurerm_cosmosdb_account.pctasks.name
  database_name         = azurerm_cosmosdb_sql_database.pctasks.name
  partition_key_path    = "/id"
  partition_key_version = 1
}

## Storage Events (for low-latency ingest)

resource "azurerm_cosmosdb_sql_container" "storage-events" {
  name                = "storage-events"
  resource_group_name = data.azurerm_cosmosdb_account.pctasks.resource_group_name
  account_name        = data.azurerm_cosmosdb_account.pctasks.name
  database_name       = azurerm_cosmosdb_sql_database.pctasks.name
  partition_key_path  = "/id"
}

## Items (for source of truth and low-latency ingest)

resource "azurerm_cosmosdb_sql_container" "items" {
  name                = "items"
  resource_group_name = data.azurerm_cosmosdb_account.pctasks.resource_group_name
  account_name        = data.azurerm_cosmosdb_account.pctasks.name
  database_name       = azurerm_cosmosdb_sql_database.pctasks.name
  partition_key_path  = "/stac_id"
}

resource "azurerm_cosmosdb_sql_container" "process-item-errors" {
  name                = "process-item-errors"
  resource_group_name = data.azurerm_cosmosdb_account.pctasks.resource_group_name
  account_name        = data.azurerm_cosmosdb_account.pctasks.name
  database_name       = azurerm_cosmosdb_sql_database.pctasks.name
  partition_key_path  = "/id"
}

## Cosmos DB Permissions

# The Task Service Principal should be able to write to the `items` container.
resource "azurerm_cosmosdb_sql_role_assignment" "pctasks-streaming-read-write" {
  resource_group_name = data.azurerm_cosmosdb_account.pctasks.resource_group_name
  account_name        = data.azurerm_cosmosdb_account.pctasks.name
  # The "000000000002" role definition grants write permissions.
  role_definition_id  = "${data.azurerm_cosmosdb_account.pctasks.id}/sqlRoleDefinitions/00000000-0000-0000-0000-000000000002"
  principal_id        = var.task_sp_object_id
  # scope               = azurerm_cosmosdb_account.lowlatency.id
  scope               = "${data.azurerm_cosmosdb_account.pctasks.id}/dbs/${azurerm_cosmosdb_sql_database.pctasks.name}/colls/${azurerm_cosmosdb_sql_container.items.name}"

}