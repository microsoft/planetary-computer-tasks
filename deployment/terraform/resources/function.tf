
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
    "PCTASKS_DISPATCH__LANDSAT_C2_L2__QUEUE_NAME" = "landsat-c2-l2",
    "PCTASKS_DISPATCH__LANDSAT_C2_L2__PREFIX"     = "https://landsateuwest.blob.core.windows.net/landsat-c2/",
    "PCTASKS_DISPATCH__LANDSAT_C2_L2__SUFFIX"     = "_MTL.xml",

    # Modis
    "PCTASKS_DISPATCH__MODIS_09A1__QUEUE_NAME" = "modis-09a1-061",
    "PCTASKS_DISPATCH__MODIS_09A1__REGEX"      = "https://modiseuwest.blob.core.windows.net/modis-061/M[OY]D09A1/.*.hdf",

    "PCTASKS_DISPATCH__MODIS_15A2H__QUEUE_NAME" = "modis-15a2h-061",
    "PCTASKS_DISPATCH__MODIS_15A2H__REGEX"      = "https://modiseuwest.blob.core.windows.net/modis-061/M[COY]D15A2H/.*.hdf",

    "PCTASKS_DISPATCH__MODIS_15A3H__QUEUE_NAME" = "modis-15a3h-061",
    "PCTASKS_DISPATCH__MODIS_15A3H__REGEX"      = "https://modiseuwest.blob.core.windows.net/modis-061/M[COY]D15A3H/.*.hdf",

    "PCTASKS_DISPATCH__MODIS_43A4__QUEUE_NAME" = "modis-43a4-061",
    "PCTASKS_DISPATCH__MODIS_43A4__REGEX"      = "https://modiseuwest.blob.core.windows.net/modis-061/MCD43A4/.*.hdf",

    "PCTASKS_DISPATCH__MODIS_64A1__QUEUE_NAME" = "modis-64a1-061",
    "PCTASKS_DISPATCH__MODIS_64A1__REGEX"      = "https://modiseuwest.blob.core.windows.net/modis-061/MCD64A1/.*.hdf",

    "PCTASKS_DISPATCH__MODIS_09Q1__QUEUE_NAME" = "modis-09q1-061",
    "PCTASKS_DISPATCH__MODIS_09Q1__REGEX"      = "https://modiseuwest.blob.core.windows.net/modis-061/M[OY]D09Q1/.*.hdf",

    "PCTASKS_DISPATCH__MODIS_10A1__QUEUE_NAME" = "modis-10a1-061",
    "PCTASKS_DISPATCH__MODIS_10A1__REGEX"      = "https://modiseuwest.blob.core.windows.net/modis-061/M[OY]D10A1/.*.hdf",

    "PCTASKS_DISPATCH__MODIS_10A2__QUEUE_NAME" = "modis-10a2-061",
    "PCTASKS_DISPATCH__MODIS_10A2__REGEX"      = "https://modiseuwest.blob.core.windows.net/modis-061/M[OY]D10A2/.*.hdf",

    "PCTASKS_DISPATCH__MODIS_11A1__QUEUE_NAME" = "modis-11a1-061",
    "PCTASKS_DISPATCH__MODIS_11A1__REGEX"      = "https://modiseuwest.blob.core.windows.net/modis-061/M[OY]D11A1/.*.hdf",

    "PCTASKS_DISPATCH__MODIS_11A2__QUEUE_NAME" = "modis-11a2-061",
    "PCTASKS_DISPATCH__MODIS_11A2__REGEX"      = "https://modiseuwest.blob.core.windows.net/modis-061/M[OY]D11A2/.*.hdf",

    "PCTASKS_DISPATCH__MODIS_13A1__QUEUE_NAME" = "modis-13a1-061",
    "PCTASKS_DISPATCH__MODIS_13A1__REGEX"      = "https://modiseuwest.blob.core.windows.net/modis-061/M[OY]D13A1/.*.hdf",

    "PCTASKS_DISPATCH__MODIS_13Q1__QUEUE_NAME" = "modis-13q1-061",
    "PCTASKS_DISPATCH__MODIS_13Q1__REGEX"      = "https://modiseuwest.blob.core.windows.net/modis-061/M[OY]D13Q1/.*.hdf",

    "PCTASKS_DISPATCH__MODIS_14A1__QUEUE_NAME" = "modis-14a1-061",
    "PCTASKS_DISPATCH__MODIS_14A1__REGEX"      = "https://modiseuwest.blob.core.windows.net/modis-061/M[OY]D14A1/.*.hdf",

    "PCTASKS_DISPATCH__MODIS_14A2__QUEUE_NAME" = "modis-14a2-061",
    "PCTASKS_DISPATCH__MODIS_14A2__REGEX"      = "https://modiseuwest.blob.core.windows.net/modis-061/M[OY]D14A2/.*.hdf",

    "PCTASKS_DISPATCH__MODIS_163GF__QUEUE_NAME" = "modis-16a3gf-061",
    "PCTASKS_DISPATCH__MODIS_163GF__REGEX"      = "https://modiseuwest.blob.core.windows.net/modis-061/M[OY]D16A3GF/.*.hdf",

    "PCTASKS_DISPATCH__MODIS_17A2H__QUEUE_NAME" = "modis-17a2h-061",
    "PCTASKS_DISPATCH__MODIS_17A2H__REGEX"      = "https://modiseuwest.blob.core.windows.net/modis-061/M[OY]D17A2H/.*.hdf",

    "PCTASKS_DISPATCH__MODIS_17A2HGF__QUEUE_NAME" = "modis-17a2hgf-061",
    "PCTASKS_DISPATCH__MODIS_17A2HGF__REGEX"      = "https://modiseuwest.blob.core.windows.net/modis-061/M[OY]D17A2HGF/.*.hdf",

    "PCTASKS_DISPATCH__MODIS_17A3HGF__QUEUE_NAME" = "modis-17a3hgf-061",
    "PCTASKS_DISPATCH__MODIS_17A3HGF__REGEX"      = "https://modiseuwest.blob.core.windows.net/modis-061/M[OY]D17A3HGF/.*.hdf",

    "PCTASKS_DISPATCH__MODIS_21A2__QUEUE_NAME" = "modis-21a2-061",
    "PCTASKS_DISPATCH__MODIS_21A2__REGEX"      = "https://modiseuwest.blob.core.windows.net/modis-061/M[OY]D21A2/.*.hdf",

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
