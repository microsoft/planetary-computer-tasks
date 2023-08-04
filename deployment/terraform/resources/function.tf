
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
    "FUNC_WORKFLOWS_COLLECTION_NAME"      = "workflows",
    "FUNC_WORKFLOW_RUNS_COLLECTION_NAME"  = "workflow-runs",
    "FUNC_STORAGE_EVENTS_COLLECTION_NAME" = "storage-events",
    "FUNC_ITEMS_COLLECTION_NAME"          = "items",
    # The storage event -> queue dispatch rules
    # GOES-GLM
    "PCTASKS_DISPATCH__GOES16_GLM__QUEUE_NAME" = "goes-glm",
    "PCTASKS_DISPATCH__GOES16_GLM__PREFIX"     = "https://goeseuwest.blob.core.windows.net/noaa-goes16/GLM-L2-LCFA/",
    "PCTASKS_DISPATCH__GOES17_GLM__QUEUE_NAME" = "goes-glm",
    "PCTASKS_DISPATCH__GOES17_GLM__PREFIX"     = "https://goeseuwest.blob.core.windows.net/noaa-goes17/GLM-L2-LCFA/",
    "PCTASKS_DISPATCH__GOES18_GLM__QUEUE_NAME" = "goes-glm",
    "PCTASKS_DISPATCH__GOES18_GLM__PREFIX"     = "https://goeseuwest.blob.core.windows.net/noaa-goes18/GLM-L2-LCFA/",
    # GOES-CMI - MCMIPC
    "PCTASKS_DISPATCH__GOES16_MCMIPC__QUEUE_NAME" = "goes-cmi",
    "PCTASKS_DISPATCH__GOES16_MCMIPC__PREFIX"     = "https://goeseuwest.blob.core.windows.net/noaa-goes16/ABI-L2-MCMIPC/",
    "PCTASKS_DISPATCH__GOES17_MCMIPC__QUEUE_NAME" = "goes-cmi",
    "PCTASKS_DISPATCH__GOES17_MCMIPC__PREFIX"     = "https://goeseuwest.blob.core.windows.net/noaa-goes17/ABI-L2-MCMIPC/",
    "PCTASKS_DISPATCH__GOES18_MCMIPC__QUEUE_NAME" = "goes-cmi",
    "PCTASKS_DISPATCH__GOES18_MCMIPC__PREFIX"     = "https://goeseuwest.blob.core.windows.net/noaa-goes18/ABI-L2-MCMIPC/",
    # GOES-CMI - MCMIPM
    "PCTASKS_DISPATCH__GOES16_MCMIPM__QUEUE_NAME" = "goes-cmi",
    "PCTASKS_DISPATCH__GOES16_MCMIPM__PREFIX"     = "https://goeseuwest.blob.core.windows.net/noaa-goes16/ABI-L2-MCMIPM/",
    "PCTASKS_DISPATCH__GOES17_MCMIPM__QUEUE_NAME" = "goes-cmi",
    "PCTASKS_DISPATCH__GOES17_MCMIPM__PREFIX"     = "https://goeseuwest.blob.core.windows.net/noaa-goes17/ABI-L2-MCMIPM/",
    "PCTASKS_DISPATCH__GOES18_MCMIPM__QUEUE_NAME" = "goes-cmi",
    "PCTASKS_DISPATCH__GOES18_MCMIPM__PREFIX"     = "https://goeseuwest.blob.core.windows.net/noaa-goes18/ABI-L2-MCMIPM/",
    # GOES-CMI - MCMIPF
    "PCTASKS_DISPATCH__GOES16_MCMIPF__QUEUE_NAME" = "goes-cmi",
    "PCTASKS_DISPATCH__GOES16_MCMIPF__PREFIX"     = "https://goeseuwest.blob.core.windows.net/noaa-goes16/ABI-L2-MCMIPF/",
    "PCTASKS_DISPATCH__GOES17_MCMIPF__QUEUE_NAME" = "goes-cmi",
    "PCTASKS_DISPATCH__GOES17_MCMIPF__PREFIX"     = "https://goeseuwest.blob.core.windows.net/noaa-goes17/ABI-L2-MCMIPF/",
    "PCTASKS_DISPATCH__GOES18_MCMIPF__QUEUE_NAME" = "goes-cmi",
    "PCTASKS_DISPATCH__GOES18_MCMIPF__PREFIX"     = "https://goeseuwest.blob.core.windows.net/noaa-goes18/ABI-L2-MCMIPF/",

    # ECMWF-forecast
    "PCTASKS_DISPATCH__ECMWF_FORECAST__QUEUE_NAME" = "ecmwf-forecast",
    "PCTASKS_DISPATCH__ECMWF_FORECAST__PREFIX"     = "https://ai4edataeuwest.blob.core.windows.net/ecmwf/",
    "PCTASKS_DISPATCH__ECMWF_FORECAST__SUFFIX"     = ".index",
    # Test
    "PCTASKS_DISPATCH__TEST_COLLECTION__QUEUE_NAME" = "test-collection",
    "PCTASKS_DISPATCH__TEST_COLLECTION__PREFIX"     = "http://azurite:10000/devstoreaccount1/",
    # Landsat-C2-L2
    "PCTASKS_DISPATCH__LANDSAT_C2_L2_FORECAST__QUEUE_NAME" = "landsat-c2-l2",
    "PCTASKS_DISPATCH__LANDSAT_C2_L2_FORECAST__PREFIX"     = "https://landsateuwest.blob.core.windows.net/landsat-c2/",
    "PCTASKS_DISPATCH__LANDSAT_C2_L2_FORECAST__SUFFIX"     = "_MTL.xml",
  }

  functions_extension_version = "~4"
  site_config {
    use_32_bit_worker        = false
    ftps_state               = "Disabled"
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
