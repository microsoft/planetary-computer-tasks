resource "azurerm_container_registry" "task-acr" {
  name                = var.task_acr_name
  resource_group_name = azurerm_resource_group.rxetl.name
  location            = azurerm_resource_group.rxetl.location
  sku                 = "Standard"
}

# Role assignments

# add the role to the identity the kubernetes cluster was assigned
resource "azurerm_role_assignment" "batch-pull" {
  scope                = azurerm_container_registry.task-acr.id
  role_definition_name = "AcrPull"
  principal_id         = var.acr_sp_object_id
}