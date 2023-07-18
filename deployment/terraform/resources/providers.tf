provider azurerm {
  features {}
}

terraform {
  required_version = ">= 0.13"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "3.28.0"
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
