terraform {
  backend "azurerm" {
    resource_group_name  = "pc-test-manual-resources"
    storage_account_name = "pctesttfstate"
    container_name       = "pctasks"
    key                  = "dev.terraform.tfstate"
  }
}