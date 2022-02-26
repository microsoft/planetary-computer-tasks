variable "region" {
  description = "Azure region for infrastructure"
  type        = string
  default     = "West Europe"
}

variable "batch_pool_id" {
  description = "Name of the default Batch pool"
  type        = string
  default     = "tasks_pool"
}

variable "username" {
  description = "Username for tagging infrastructure dedicated to you"
  type        = string
}

# Resource module variables

variable "acr_sp_object_id" {
  type    = string
}

variable "acr_sp_client_id" {
  type    = string
}

variable "acr_sp_client_secret" {
  type    = string
}

variable "task_sp_tenant_id" {
  type    = string
}

variable "task_sp_client_id" {
  type    = string
}

variable "task_sp_client_secret" {
  type    = string
}

variable "task_acr_name" {
    type = string
}

variable "db_username" {
    type = string
}

variable "db_password" {
    type = string
}

variable "db_storage_mb" {
    type = number
    default = 32768  # 5 GB
}

variable "min_low_priority" {
    type = number
    default = 0
    description = "Minimum number of low priority Batch nodes to keep running"
}
