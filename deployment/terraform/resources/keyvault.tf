resource "azurerm_key_vault" "rxetl" {
  name                = "${local.stack_id}-${var.environment}-rxetlkv"
  location            = azurerm_resource_group.rxetl.location
  resource_group_name = azurerm_resource_group.rxetl.name
  tenant_id           = data.azurerm_client_config.current.tenant_id
  sku_name            = "premium"
}

resource "azurerm_key_vault_access_policy" "deployer" {
  key_vault_id = azurerm_key_vault.rxetl.id
  tenant_id    = data.azurerm_client_config.current.tenant_id
  object_id    = data.azurerm_client_config.current.object_id

  secret_permissions = [
    "Get", "Set", "List", "Delete"
  ]
}

resource "azurerm_key_vault_access_policy" "function_app" {
  key_vault_id = azurerm_key_vault.rxetl.id
  tenant_id    = azurerm_function_app.rxetl.identity.0.tenant_id
  object_id    = azurerm_function_app.rxetl.identity.0.principal_id

  secret_permissions = [
    "Get", "List"
  ]
}

# Store database information as a secret

resource "azurerm_key_vault_secret" "pgstac-connection-string" {
  name         = "pgstac-connection-string"
  value        = "postgresql://${azurerm_postgresql_flexible_server.db.administrator_login}:${azurerm_postgresql_flexible_server.db.administrator_password}@${azurerm_postgresql_flexible_server.db.fqdn}:5432/postgis"
  key_vault_id = azurerm_key_vault.rxetl.id
}

# Store task credentials as a secret

resource "azurerm_key_vault_secret" "task-tenant-id" {
  name         = "task-tenant-id"
  value        = var.task_sp_tenant_id
  key_vault_id = azurerm_key_vault.rxetl.id
}

resource "azurerm_key_vault_secret" "task-client-id" {
  name         = "task-client-id"
  value        = var.task_sp_tenant_id
  key_vault_id = azurerm_key_vault.rxetl.id
}

resource "azurerm_key_vault_secret" "task-client-secret" {
  name         = "task-client-secret"
  value        = var.task_sp_tenant_id
  key_vault_id = azurerm_key_vault.rxetl.id
}
