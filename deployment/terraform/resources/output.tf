output "environment" {
  value = var.environment
}

output "resource_group" {
  value = azurerm_resource_group.pctasks.name
}

output "location" {
  value = local.location
}

output "tenant_id" {
  value = data.azurerm_client_config.current.tenant_id
}

## Ingress

output "secret_provider_keyvault_name" {
  value = var.secret_provider_keyvault_name
}

output "secret_provider_managed_identity_id" {
  value = azurerm_kubernetes_cluster.pctasks.key_vault_secrets_provider[0].secret_identity[0].client_id
}

output "secret_provider_keyvault_secret" {
  value = var.secret_provider_keyvault_secret
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

output "internal_ingress_ip" {
  value = var.k8s_vnet_ingress_address
}

output "cloudapp_hostname" {
  value = "${azurerm_public_ip.pctasks.domain_name_label}.${local.location}.cloudapp.azure.com"
}

output "pctasks_server_replica_count" {
  value = var.pctasks_server_replica_count
}

output "pctasks_workflow_identity_client_id" {
  value = azurerm_user_assigned_identity.workflows.client_id
}

output "pctasks_workflow_identity_tenant_id" {
  value = azurerm_user_assigned_identity.workflows.tenant_id
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

output "batch_user_assigned_identity_id" {
  value = azurerm_user_assigned_identity.pctasks.id
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

output "aks_streaming_task_node_group_name" {
  value = var.aks_streaming_task_node_group_name
}
