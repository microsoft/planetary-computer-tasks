output "environment" {
  value = var.environment
}

output "resource_group" {
  value = azurerm_resource_group.rxetl.name
}

output "location" {
  value = local.location
}

## AKS

output "cluster_name" {
  value = azurerm_kubernetes_cluster.rxetl.name
}

output "cluster_cert_issuer" {
  value = var.cluster_cert_issuer
}

output "cluster_cert_server" {
  value = var.cluster_cert_server
}

output "ingress_ip" {
  value = azurerm_public_ip.rxetl.ip_address
}

output "dns_label" {
  value = azurerm_public_ip.rxetl.domain_name_label
}

output "pctasks_server_replica_count" {
  value = var.pctasks_server_replica_count
}

## Functions

output "function_app_name" {
  value = azurerm_function_app.rxetl.name
}

## Batch

output "batch_account_name" {
  value = azurerm_batch_account.rxetl.name
}

output "batch_url" {
  value = "https://${azurerm_batch_account.rxetl.account_endpoint}"
}

output "batch_key" {
  value = azurerm_batch_account.rxetl.primary_access_key
}

output "batch_default_pool_id" {
  value = var.batch_default_pool_id
}

output "batch_nodepool_subnet" {
  value = azurerm_subnet.nodepool_subnet.id
}


## ACR

output "task_acr_name" {
  value = var.task_acr_name
}

output "component_acr_name" {
  value = var.component_acr_name
}

output "pctasks_server_image_tag" {
  value = var.pctasks_server_image_tag
}

output "pctasks_run_image_tag" {
  value = var.pctasks_run_image_tag
}

## Database

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

output "sa_tables_account_url" {
  value = azurerm_storage_account.rxetl.primary_table_endpoint
}

output "sa_blob_account_url" {
  value = azurerm_storage_account.rxetl.primary_blob_endpoint
}

output "sa_account_name" {
  value = azurerm_storage_account.rxetl.name
}

output "sa_account_key" {
  value     = azurerm_storage_account.rxetl.primary_access_key
  sensitive = true
}

output "sa_connection_string" {
  value = azurerm_storage_account.rxetl.primary_connection_string
}

## Keyvault

output "keyvault_url" {
  value = azurerm_key_vault.rxetl.vault_uri
}

output "kv_sp_tenant_id" {
  value = var.kv_sp_tenant_id
}

output "kv_sp_client_id" {
  value = var.kv_sp_client_id
}

output "kv_sp_client_secret" {
  value = var.kv_sp_client_secret
}

## PCTasks Server

output "pctasks_server_account_key" {
  value     = var.pctasks_server_account_key
  sensitive = true
}

output "pctasks_server_sp_tenant_id" {
  value  = var.pctasks_server_sp_tenant_id
  sensitive = true
}

output "pctasks_server_sp_client_id" {
  value = var.pctasks_server_sp_client_id
  sensitive = true
}

output "pctasks_server_sp_client_secret" {
  value = var.pctasks_server_sp_client_secret
  sensitive = true
}