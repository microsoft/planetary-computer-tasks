resource "azurerm_application_insights" "pctasks_application_insights" {
  name                = "${local.prefix}-app-insights"
  location            = azurerm_resource_group.pctasks.location
  resource_group_name = azurerm_resource_group.pctasks.name
  application_type    = "web"
}