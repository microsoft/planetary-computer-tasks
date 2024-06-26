data "azurerm_key_vault" "pctasks" {
  name                = var.pctasks_task_kv
  resource_group_name = var.pctasks_task_kv_resource_group_name
}

# Store database information as a secret

resource "azurerm_key_vault_secret" "pgstac-connection-string" {
  name         = "pgstac-connection-string"
  value        = var.stac_db_connection_string
  key_vault_id = data.azurerm_key_vault.pctasks.id
}

resource "azurerm_key_vault_secret" "task-application-insights-connection-string" {
  name = "task-application-insights-connection-string"
  value = azurerm_application_insights.pctasks.connection_string
  key_vault_id = data.azurerm_key_vault.pctasks.id
}

# API Management access key

data "azurerm_key_vault" "deploy_secrets" {
  name                = var.deploy_secrets_kv_name
  resource_group_name = var.deploy_secrets_kv_rg
}

data "azurerm_key_vault_secret" "access_key" {
  name         = var.access_key_secret_name
  key_vault_id = data.azurerm_key_vault.deploy_secrets.id
}

data "azurerm_key_vault_secret" "backend_app_id" {
  name         = var.backend_api_app_id_secret_name
  key_vault_id = data.azurerm_key_vault.deploy_secrets.id
}

# Ensure the application can access the key vault
resource "azurerm_role_assignment" "pctasks-keyvault-access" {
  scope                = data.azurerm_key_vault.deploy_secrets.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = each.key

  for_each = toset([
    azurerm_linux_function_app.pctasks.identity.0.principal_id,
    azurerm_user_assigned_identity.workflows.principal_id,
  ])
}