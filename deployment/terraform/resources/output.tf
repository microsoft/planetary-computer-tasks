output "environment" {
  value = var.environment
}

output "resource_group" {
  value = azurerm_resource_group.pctasks.name
}

output "location" {
  value = local.location
}

## AKS

output "cluster_name" {
  value = azurerm_kubernetes_cluster.pctasks.name
}

output "cluster_cert_issuer" {
  value = var.cluster_cert_issuer
}

output "cluster_cert_server" {
  value = var.cluster_cert_server
}

output "ingress_ip" {
  value = azurerm_public_ip.pctasks.ip_address
}

output "dns_label" {
  value = azurerm_public_ip.pctasks.domain_name_label
}

output "cloudapp_hostname" {
  value = "${azurerm_public_ip.pctasks.domain_name_label}.${local.location}.cloudapp.azure.com"
}

output "pctasks_server_replica_count" {
  value = var.pctasks_server_replica_count
}

## Functions

output "function_app_name" {
  value = azurerm_linux_function_app.pctasks.name
}

## Batch

output "batch_account_name" {
  value = azurerm_batch_account.pctasks.name
}

output "batch_url" {
  value = "https://${azurerm_batch_account.pctasks.account_endpoint}"
}

output "batch_key" {
  value = azurerm_batch_account.pctasks.primary_access_key
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

# Storage account

output "sa_tables_account_url" {
  value = azurerm_storage_account.pctasks.primary_table_endpoint
}

output "sa_blob_account_url" {
  value = azurerm_storage_account.pctasks.primary_blob_endpoint
}

output "sa_account_name" {
  value = azurerm_storage_account.pctasks.name
}

output "sa_account_key" {
  value     = azurerm_storage_account.pctasks.primary_access_key
  sensitive = true
}

output "sa_connection_string" {
  value = azurerm_storage_account.pctasks.primary_connection_string
}

## Keyvault

output "keyvault_url" {
  value = data.azurerm_key_vault.pctasks.vault_uri
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

output "kv_access_key" {
  value = data.azurerm_key_vault_secret.access_key.value
}

## API Management

output "api_management_name" {
  value = azurerm_api_management.pctasks.name
}

# Application Insights

output "instrumentation_key" {
  value = azurerm_application_insights.pctasks.instrumentation_key
}

## PCTasks Server

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

output "argo_wf_node_group_name" {
  value = var.argo_wf_node_group_name
}

## CosmosDB

output "cosmosdb_url" {
  value = data.azurerm_cosmosdb_account.pctasks.endpoint
}

output "cosmosdb_key" {
  value = data.azurerm_cosmosdb_account.pctasks.primary_key
}

## AKS

output "aks_streaming_task_node_group" {
  value = var.aks_streaming_task_node_group
}

output "streaming_taskio_sp_tenant_id" {
  value = var.streaming_taskio_sp_tenant_id
}

output "streaming_taskio_sp_client_id" {
  value = var.streaming_taskio_sp_client_id
}

output "streaming_taskio_sp_client_secret" {
  value = var.streaming_taskio_sp_client_secret
  sensitive = true
}