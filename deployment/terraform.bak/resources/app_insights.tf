resource "azurerm_log_analytics_workspace" "rxetl" {
  name                = "${local.prefix}-azm-ws"
  location            = azurerm_resource_group.rxetl.location
  resource_group_name = azurerm_resource_group.rxetl.name
  sku                 = "PerGB2018"
  retention_in_days   = 30
}

resource "azurerm_application_insights" "rxetl" {
  name                = "${local.prefix}-ai"
  location            = azurerm_resource_group.rxetl.location
  resource_group_name = azurerm_resource_group.rxetl.name
  workspace_id        = azurerm_log_analytics_workspace.rxetl.id
  application_type    = "web"
}
