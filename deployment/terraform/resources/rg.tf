resource "azurerm_resource_group" "pctasks" {
  name     = "rg-${local.full_prefix}"
  location = var.region

  tags = {
    "ringValue" = "r0"
  }
}
