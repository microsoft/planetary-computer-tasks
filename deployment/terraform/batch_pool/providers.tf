provider azurerm {
  features {}
  skip_provider_registration = true
  use_oidc = true
}

terraform {
  required_version = ">= 0.13"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "3.97.1"
    }
  }
}
