resource "azurerm_storage_account" "pctasks" {
  name                     = local.nodash_prefix
  resource_group_name      = azurerm_resource_group.pctasks.name
  location                 = azurerm_resource_group.pctasks.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
}

# Tables

resource "azurerm_storage_table" "imagekeys" {
  name                 = "imagekeys"
  storage_account_name = azurerm_storage_account.pctasks.name
}

# Blob

resource "azurerm_storage_container" "tasklogs" {
  name                  = "tasklogs"
  storage_account_name  = azurerm_storage_account.pctasks.name
  container_access_type = "private"
}

resource "azurerm_storage_container" "taskio" {
  name                  = "taskio"
  storage_account_name  = azurerm_storage_account.pctasks.name
  container_access_type = "private"
}

resource "azurerm_storage_container" "code" {
  name                  = "code"
  storage_account_name  = azurerm_storage_account.pctasks.name
  container_access_type = "private"
}

# Access Policies

resource "azurerm_role_assignment" "pctasks-server-blob-access" {
  scope                = azurerm_storage_account.pctasks.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = var.pctasks_server_sp_object_id
}

resource "azurerm_role_assignment" "pctasks-server-queue-access" {
  scope                = azurerm_storage_account.pctasks.id
  role_definition_name = "Storage Queue Data Contributor"
  principal_id         = var.pctasks_server_sp_object_id
}

resource "azurerm_role_assignment" "pctasks-server-table-access" {
  scope                = azurerm_storage_account.pctasks.id
  role_definition_name = "Storage Table Data Contributor"
  principal_id         = var.pctasks_server_sp_object_id
}
