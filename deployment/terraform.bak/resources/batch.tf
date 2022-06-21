resource "azurerm_storage_account" "rxetl-batch" {
  name                     = "${local.stack_id}${var.environment}rxetlbatchsa"
  resource_group_name      = azurerm_resource_group.rxetl.name
  location                 = azurerm_resource_group.rxetl.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
}

resource "azurerm_batch_account" "rxetl" {
  name                 = "${local.stack_id}${var.environment}rxetlbatch"
  resource_group_name  = azurerm_resource_group.rxetl.name
  location             = azurerm_resource_group.rxetl.location
  pool_allocation_mode = "BatchService"
  storage_account_id   = azurerm_storage_account.rxetl-batch.id

  tags = {
    ManagedBy   = "AI4E"
    Environment = var.environment
  }
}
