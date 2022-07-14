resource "azurerm_resource_group" "rxetl" {
  name     = "${local.full_prefix}_rg"
  location = var.region

  tags = {
    "ringValue" = "r0"
  }
}
