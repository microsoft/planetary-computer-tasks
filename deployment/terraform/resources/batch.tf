resource "azurerm_storage_account" "pctasks-batch" {
  name                     = substr("stb${local.nodash_prefix}", 0, 24)
  resource_group_name      = azurerm_resource_group.pctasks.name
  location                 = azurerm_resource_group.pctasks.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
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
