resource "azurerm_storage_account" "pctasks-batch" {
  name                            = substr("stb${local.nodash_prefix}", 0, 24)
  resource_group_name             = azurerm_resource_group.pctasks.name
  location                        = azurerm_resource_group.pctasks.location
  account_tier                    = "Standard"
  account_replication_type        = "LRS"
  allow_nested_items_to_be_public = false

}

resource "azurerm_batch_account" "pctasks" {
  name                                = local.nodash_prefix
  resource_group_name                 = azurerm_resource_group.pctasks.name
  location                            = azurerm_resource_group.pctasks.location
  pool_allocation_mode                = "BatchService"
  storage_account_id                  = azurerm_storage_account.pctasks-batch.id
  storage_account_authentication_mode = "StorageKeys"

  tags = {
    ManagedBy   = "AI4E"
    Environment = var.environment
  }
}

resource "azurerm_user_assigned_identity" "pctasks" {
  name                = "mi-${local.full_prefix}"
  resource_group_name = azurerm_resource_group.pctasks.name
  location            = azurerm_resource_group.pctasks.location
}

resource "azurerm_role_assignment" "batch-acr-pull-task" {
  scope                = data.azurerm_container_registry.task_acr.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_user_assigned_identity.pctasks.principal_id
}

# We need this if and only if the component acr differs from the task acr.
# If they match, then the assignment fails (because it duplicates the
# above assignment.)
# resource "azurerm_role_assignment" "batch-acr-pull-component" {
#   scope                = data.azurerm_container_registry.component_acr.id
#   role_definition_name = "AcrPull"
#   principal_id         = azurerm_user_assigned_identity.pctasks.principal_id
# }