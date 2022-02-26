output "environment" {
  value = var.environment
}

output "resource_group" {
  value = azurerm_resource_group.rxetl.name
}

output "function_app_name" {
  value = azurerm_function_app.rxetl.name
}

output "batch_account_name" {
  value = azurerm_batch_account.rxetl.name
}

output "batch_nodepool_subnet" {
  value = azurerm_subnet.nodepool_subnet.id
}

output "acr_name" {
  value = var.task_acr_name
}

output "acr_client_id" {
  value = var.acr_sp_client_id
}

output "acr_client_secret" {
  value = var.acr_sp_client_secret
}

output "db_fqdn" {
  value = azurerm_postgresql_flexible_server.db.fqdn
}

output "db_name" {
  value = azurerm_postgresql_flexible_server_database.postgis.name
}

output "db_username" {
  value = azurerm_postgresql_flexible_server.db.administrator_login
}

output "db_password" {
  value     = azurerm_postgresql_flexible_server.db.administrator_password
  sensitive = true
}

# Storage account

output "tables_account_url" {
  value = azurerm_storage_account.rxetl.primary_table_endpoint
}

output "tables_account_name" {
  value = azurerm_storage_account.rxetl.name
}

output "tables_account_key" {
  value     = azurerm_storage_account.rxetl.primary_access_key
  sensitive = true
}

output "tables_connection_string" {
  value = azurerm_storage_account.rxetl.primary_connection_string
}