provider "azurerm" {
  features {}
  skip_provider_registration = true
  use_oidc                   = true

  # This could be used instead of temporarily enabling shared key access once
  # this issue is resolved.
  # https://github.com/hashicorp/terraform-provider-azurerm/issues/15083
  # storage_use_azuread = true
}

terraform {
  required_version = ">= 0.13"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "3.110.0"
    }
  }
}

data "azurerm_client_config" "current" {
}


# Terraform stuff to include
# 1. This provider
# 2. Cosmos DB containers
# 3. The AKS Node Pool
# 4. The Kubernetes namespace, secrets
