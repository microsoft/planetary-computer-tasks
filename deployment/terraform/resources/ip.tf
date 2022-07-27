resource "azurerm_public_ip" "pctasks" {
  name                = "ip-${local.prefix}"
  domain_name_label   = local.prefix
  resource_group_name = azurerm_kubernetes_cluster.pctasks.node_resource_group
  location            = azurerm_resource_group.pctasks.location
  allocation_method   = "Static"
  sku                 = "Standard"

  tags = {
    environment = var.environment

    # This has to be manually changed during deployes
    # If you let terraform delete it it can break the DNS linkage.
    # See https://github.com/terraform-providers/terraform-provider-azurerm/issues/7034
    # and https://github.com/terraform-providers/terraform-provider-azurerm/pull/11020#issuecomment-802606941

    # k8s-azure-dns-label-service = "pc/nginx-ingress-ingress-nginx-controller"
  }
}
