variable "region" {
  description = "Azure region for infrastructure"
  type        = string
  default     = "West Europe"
}

# Batch

variable "batch_default_pool_id" {
  description = "Name of the default Batch pool"
  type        = string
  default     = "tasks_pool"
}

variable "min_low_priority" {
  type        = number
  default     = 0
  description = "Minimum number of low priority Batch nodes to keep running"
}

# ACR

variable "task_acr_resource_group" {
  type    = string
  default = "pc-test-manual-resources"
}

variable "task_acr_name" {
  type    = string
  default = "pccomponentstest"
}

variable "component_acr_resource_group" {
  type    = string
  default = "pc-test-manual-resources"
}

variable "component_acr_name" {
  type    = string
  default = "pccomponentstest"
}

variable "pctasks_server_image_tag" {
  type    = string
  default = "latest"
}

variable "pctasks_run_image_tag" {
  type    = string
  default = "latest"
}


## Keyvault

variable "deploy_secrets_kv_name" {
  type = string
}

variable "deploy_secrets_kv_rg" {
  type = string
}

variable "access_key_secret_name" {
  type = string
}

variable "backend_api_app_id_secret_name" {
  type = string
}

## Database

variable "stac_db_connection_string" {
  type = string
}

variable "cosmosdb_account_name" {
  type = string
}

variable "cosmosdb_resource_group" {
  type = string
}

## AKS

variable "aks_streaming_task_node_group_name" {
  type        = string
  default     = "pc-lowlatency"
  description = "The name of the node group that will run streaming tasks"
}

# APIM

variable "apim_sku_name" {
  type    = string
  default = "Developer_1"
}
