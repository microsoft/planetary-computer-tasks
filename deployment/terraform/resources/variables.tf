variable "environment" {
  type = string
}

variable "region" {
  type = string
}

variable "batch_pool_id" {
  type = string
}

variable "acr_sp_object_id" {
  type = string
}

variable "acr_sp_client_id" {
  type = string
}

variable "acr_sp_client_secret" {
  type = string
}

variable "task_acr_name" {
  type    = string
  default = "pccomponentstest"
}

variable "task_sp_tenant_id" {
  type = string
}

variable "task_sp_client_id" {
  type = string
}

variable "task_sp_client_secret" {
  type = string
}

variable "db_username" {
  type = string
}

variable "db_password" {
  type = string
}

variable "db_storage_mb" {
  type    = number
  default = 32768
}

# ---------------
# Local variables

locals {
  stack_id              = "pctrxetl"
  location              = lower(replace(var.region, " ", ""))
  prefix                = "${local.stack_id}-${var.environment}"
  full_prefix           = "${local.stack_id}-${local.location}-${var.environment}"
  nodash_prefix         = "${local.stack_id}${var.environment}"
  deploy_secrets_prefix = "${local.stack_id}-${var.environment}"
}
