
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
    "ENABLE_ORYX_BUILD"                  = "true",
    "SCM_DO_BUILD_DURING_DEPLOYMENT"     = "true",
    "APP_INSIGHTS_IKEY"                  = azurerm_application_insights.pctasks.instrumentation_key,
    "APPINSIGHTS_INSTRUMENTATIONKEY"     = azurerm_application_insights.pctasks.instrumentation_key,
    "AzureStorageQueuesConnectionString" = azurerm_storage_account.pctasks.primary_connection_string,
    "AzureWebJobsDisableHomepage"        = true,

    "PCTASKS_COSMOSDB__URL" = data.azurerm_cosmosdb_account.pctasks.endpoint,
    "PCTASKS_COSMOSDB__KEY" = data.azurerm_cosmosdb_account.pctasks.primary_key,
    # Set trigger app setting separately to avoid issues with __ in env var names
    "FUNC_COSMOSDB_CONN_STR" = "AccountEndpoint=${data.azurerm_cosmosdb_account.pctasks.endpoint};AccountKey=${data.azurerm_cosmosdb_account.pctasks.primary_key};"
  }

  functions_extension_version = "~4"
  site_config {
    use_32_bit_worker = false
    application_stack {
      python_version = "3.8"
    }
  }
}
