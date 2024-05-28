variable "name" {
  type = string
}

variable "resource_group_name" {
  type = string
}

variable "account_name" {
  type = string
}

variable "display_name" {
  type = string
}

variable "vm_size" {
  type = string
}

variable "max_tasks_per_node" {
  type = number
}

variable "subnet_id" {
  type = string
}

variable "min_dedicated" {
  type = number
}

variable "max_dedicated" {
  type = number
}

variable "min_low_priority" {
  type = number
}

variable "max_low_priority" {
  type = number
}

variable "max_increase_per_scale" {
  type = number
}

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# ACR

variable "acr_name" {
  type = string
}

variable "user_assigned_identity_id" {
  type = string
}