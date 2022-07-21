variable "environment" {
  type = string
}

variable "region" {
  type = string
}

## AKS

variable "cluster_cert_issuer" {
  type = string
}

variable "cluster_cert_server" {
  type = string
}

variable "k8s_version" {
  type = string
}

variable "k8s_orchestrator_version" {
  type = string
}

variable "aks_node_count" {
  type = number
  default = 1
}

variable "pctasks_server_replica_count" {
  type    = number
  default = 1
}

## Batch

variable "batch_default_pool_id" {
  type = string
}

## ACR

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

## Database

variable "stac_db_connection_string" {
  type = string
}

## Keyvault

variable "task_sp_tenant_id" {
  type = string
}

variable "task_sp_client_id" {
  type = string
}

variable "task_sp_client_secret" {
  type = string
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

# ---------------
# Local variables

locals {
  stack_id              = "pctaskstest"
  location              = lower(replace(var.region, " ", ""))
  prefix                = "${local.stack_id}-${var.environment}"
  full_prefix           = "${local.stack_id}-${var.environment}-${local.location}"
  nodash_prefix         = "${local.stack_id}${var.environment}"
  deploy_secrets_prefix = "${local.stack_id}-${var.environment}"
}
