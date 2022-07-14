resource "azurerm_log_analytics_workspace" "pctasks" {
  name                = "log-${local.prefix}"
  location            = azurerm_resource_group.pctasks.location
  resource_group_name = azurerm_resource_group.pctasks.name
  sku                 = "PerGB2018"
  retention_in_days   = 30
}

resource "azurerm_application_insights" "pctasks" {
  name                = "appi-${local.prefix}"
  location            = azurerm_resource_group.pctasks.location
  resource_group_name = azurerm_resource_group.pctasks.name
  workspace_id        = azurerm_log_analytics_workspace.pctasks.id
  application_type    = "web"
}
