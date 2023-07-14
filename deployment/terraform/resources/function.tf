
resource "azurerm_service_plan" "pctasks" {
  name                = "plan-${local.prefix}"
  location            = azurerm_resource_group.pctasks.location
  resource_group_name = azurerm_resource_group.pctasks.name
  os_type             = "Linux"
  sku_name            = "Y1"
}

resource "azurerm_linux_function_app" "pctasks" {
  name                       = "func-${local.prefix}"
  location                   = azurerm_resource_group.pctasks.location
  resource_group_name        = azurerm_resource_group.pctasks.name
  service_plan_id            = azurerm_service_plan.pctasks.id
  storage_account_name       = azurerm_storage_account.pctasks.name
  storage_account_access_key = azurerm_storage_account.pctasks.primary_access_key
  https_only                 = true

  identity {
    type = "SystemAssigned"
  }

  app_settings = {
    "ENABLE_ORYX_BUILD"                     = "true",
    "SCM_DO_BUILD_DURING_DEPLOYMENT"        = "true",
    "PCTASK_APPINSIGHTS_INSTRUMENTATIONKEY" = azurerm_application_insights.pctasks.instrumentation_key,
    "AzureStorageQueuesConnectionString"    = azurerm_storage_account.pctasks.primary_connection_string,
    "AzureWebJobsDisableHomepage"           = true,

    "PCTASKS_COSMOSDB__URL" = data.azurerm_cosmosdb_account.pctasks.endpoint,
    "PCTASKS_COSMOSDB__KEY" = data.azurerm_cosmosdb_account.pctasks.primary_key,
    # Set trigger app setting separately to avoid issues with __ in env var names
    "FUNC_COSMOSDB_CONN_STR" = "AccountEndpoint=${data.azurerm_cosmosdb_account.pctasks.endpoint};AccountKey=${data.azurerm_cosmosdb_account.pctasks.primary_key};",
    # Sets the Storage Account to use for low-latency queues
    "FUNC_STORAGE_QUEUE_ACCOUNT_URL" = azurerm_storage_account.pctasks.primary_queue_endpoint,
    # Sets the name of the Cosmos DB containers to watch dynamically, to enable changing during unit tests.
    "FUNC_WORKFLOWS_COLLECTION_NAME" = "workflows",
    "FUNC_WORKFLOW_RUNS_COLLECTION_NAME" = "workflow-runs",
    "FUNC_STORAGE_EVENTS_COLLECTION_NAME" = "storage-events",
    "FUNC_ITEMS_COLLECTION_NAME" = "items",
  }

  functions_extension_version = "~4"
  site_config {
    use_32_bit_worker = false
    ftps_state        = "Disabled"
    application_insights_key = azurerm_application_insights.pctasks.instrumentation_key

    application_stack {
      python_version = "3.10"
    }
  }

  lifecycle {
    ignore_changes = [
      # Ignore changes to tags, e.g. because a management agent
      # updates these based on some ruleset managed elsewhere.
      tags,
    ]
  }
}
