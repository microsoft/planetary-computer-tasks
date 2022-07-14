resource "azurerm_key_vault" "pctasks" {
  name                = "kv-${local.prefix}"
  location            = azurerm_resource_group.pctasks.location
  resource_group_name = azurerm_resource_group.pctasks.name
  tenant_id           = data.azurerm_client_config.current.tenant_id
  sku_name            = "premium"
}

resource "azurerm_key_vault_access_policy" "deployer" {
  key_vault_id = azurerm_key_vault.pctasks.id
  tenant_id    = data.azurerm_client_config.current.tenant_id
  object_id    = data.azurerm_client_config.current.object_id

  secret_permissions = [
    "Get", "Set", "List", "Delete"
  ]
}

resource "azurerm_key_vault_access_policy" "function_app" {
  key_vault_id = azurerm_key_vault.pctasks.id
  tenant_id    = azurerm_function_app.pctasks.identity.0.tenant_id
  object_id    = azurerm_function_app.pctasks.identity.0.principal_id

  secret_permissions = [
    "Get", "List"
  ]
}

# Store database information as a secret

resource "azurerm_key_vault_secret" "pgstac-connection-string" {
  name         = "pgstac-connection-string"
  value        = var.stac_db_connection_string
  key_vault_id = azurerm_key_vault.pctasks.id
}

# Store task credentials as a secret

resource "azurerm_key_vault_secret" "task-tenant-id" {
  name         = "task-tenant-id"
  value        = var.task_sp_tenant_id
  key_vault_id = azurerm_key_vault.pctasks.id
}

resource "azurerm_key_vault_secret" "task-client-id" {
  name         = "task-client-id"
  value        = var.task_sp_client_id
  key_vault_id = azurerm_key_vault.pctasks.id
}

resource "azurerm_key_vault_secret" "task-client-secret" {
  name         = "task-client-secret"
  value        = var.task_sp_client_secret
  key_vault_id = azurerm_key_vault.pctasks.id
}
