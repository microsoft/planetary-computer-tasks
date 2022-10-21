variable "username" {
  description = "Username for tagging infrastructure dedicated to you"
  type        = string
}

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
    type = number
    default = 0
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

variable "task_acr_sp_object_id" {
  type = string
}

variable "task_acr_sp_client_id" {
  type = string
}

variable "task_acr_sp_client_secret" {
  type = string
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

variable "task_sp_tenant_id" {
  type    = string
}

variable "task_sp_client_id" {
  type    = string
}

variable "task_sp_client_secret" {
  type    = string
}

variable "kv_sp_tenant_id" {
  type    = string
}

variable "kv_sp_client_id" {
  type    = string
}

variable "kv_sp_client_secret" {
  type    = string
}

variable "deploy_secrets_kv_name" {
  type    = string
}

variable deploy_secrets_kv_rg {
  type    = string
}

variable access_key_secret_name {
  type    = string
}

variable backend_api_app_id_secret_name {
  type    = string
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

## PCTasks Server

variable "pctasks_server_sp_tenant_id" {
  type    = string
}

variable "pctasks_server_sp_client_id" {
  type    = string
}

variable "pctasks_server_sp_client_secret" {
  type    = string
}

variable "pctasks_server_sp_object_id" {
  type    = string
}
