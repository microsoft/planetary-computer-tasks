resource "azurerm_public_ip" "pctasks" {
  name                = "ip-${local.prefix}"
  domain_name_label   = local.prefix
  resource_group_name = azurerm_kubernetes_cluster.pctasks.node_resource_group
  location            = azurerm_resource_group.pctasks.location
  allocation_method   = "Static"
  sku                 = "Standard"

  tags = {
    environment = var.environment
  }

  lifecycle {
    ignore_changes = [
      # Ignore changes to tags, e.g. because a management agent
      # updates these based on some ruleset managed elsewhere.
      tags,
    ]
  }
}
