data "azurerm_container_registry" "task_acr" {
  name                = var.task_acr_name
  resource_group_name = var.task_acr_resource_group
}

data "azurerm_container_registry" "component_acr" {
  name                = var.component_acr_name
  resource_group_name = var.component_acr_resource_group
}

# Role assignments

# Note:  role to the batch account task acr service principal
# should have AcrPull access to the task acr.

# add the role to the identity the kubernetes cluster was assigned
resource "azurerm_role_assignment" "attach_acr" {
  scope                = data.azurerm_container_registry.component_acr.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_kubernetes_cluster.pctasks.kubelet_identity[0].object_id
}