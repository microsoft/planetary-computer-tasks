data "azurerm_cosmosdb_account" "pctasks" {
  name                = var.cosmosdb_account_name
  resource_group_name = var.cosmosdb_resource_group
}

resource "azurerm_cosmosdb_sql_database" "pctasks" {
  name                = "pctasks-db"
  resource_group_name = data.azurerm_cosmosdb_account.pctasks.resource_group_name
  account_name        = data.azurerm_cosmosdb_account.pctasks.name
}

resource "azurerm_cosmosdb_sql_container" "workflowruns" {
  name                  = "workflow-runs"
  resource_group_name   = data.azurerm_cosmosdb_account.pctasks.resource_group_name
  account_name          = data.azurerm_cosmosdb_account.pctasks.name
  database_name         = azurerm_cosmosdb_sql_database.pctasks.name
  partition_key_path    = "/run_id"
}

resource "azurerm_cosmosdb_sql_container" "workflowruns" {
  name                  = "datasets"
  resource_group_name   = data.azurerm_cosmosdb_account.pctasks.resource_group_name
  account_name          = data.azurerm_cosmosdb_account.pctasks.name
  database_name         = azurerm_cosmosdb_sql_database.pctasks.name
  partition_key_path    = "/run_id"
}

resource "azurerm_cosmosdb_sql_container" "workflows" {
  name                  = "workflows"
  resource_group_name   = data.azurerm_cosmosdb_account.pctasks.resource_group_name
  account_name          = data.azurerm_cosmosdb_account.pctasks.name
  database_name         = azurerm_cosmosdb_sql_database.pctasks.name
  partition_key_path    = "/run_id"
  partition_key_version = 1
}