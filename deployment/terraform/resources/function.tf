
resource "azurerm_app_service_plan" "rxetl" {
  name                = "${local.prefix}-function-app-plan"
  location            = azurerm_resource_group.rxetl.location
  resource_group_name = azurerm_resource_group.rxetl.name
  kind                = "functionapp"
  reserved            = true

  sku {
    tier = "Dynamic"
    size = "Y1"
  }
}

resource "azurerm_function_app" "rxetl" {
  name                       = "${local.prefix}-func-app"
  location                   = azurerm_resource_group.rxetl.location
  resource_group_name        = azurerm_resource_group.rxetl.name
  app_service_plan_id        = azurerm_app_service_plan.rxetl.id
  storage_account_name       = azurerm_storage_account.rxetl.name
  storage_account_access_key = azurerm_storage_account.rxetl.primary_access_key
  https_only                 = true

  identity {
    type = "SystemAssigned"
  }

  app_settings = {
    "ENABLE_ORYX_BUILD"                  = "true",
    "SCM_DO_BUILD_DURING_DEPLOYMENT"     = "true",
    "FUNCTIONS_WORKER_RUNTIME"           = "python",
    "APP_INSIGHTS_IKEY"                  = azurerm_application_insights.rxetl.instrumentation_key,
    "APPINSIGHTS_INSTRUMENTATIONKEY"     = azurerm_application_insights.rxetl.instrumentation_key,
    "AzureStorageQueuesConnectionString" = azurerm_storage_account.rxetl.primary_connection_string,
    "AzureWebJobsDisableHomepage"        = true,

    # Function queue trigger bindings ##
    "FUNC_NOTIFY_QUEUE_CONN_STR"      = azurerm_storage_account.rxetl.primary_connection_string,
    "FUNC_ROUTER_QUEUE_CONN_STR"      = azurerm_storage_account.rxetl.primary_connection_string,
    "FUNC_WORKFLOW_QUEUE_CONN_STR"    = azurerm_storage_account.rxetl.primary_connection_string,
    "FUNC_TASKS_QUEUE_CONN_STR"       = azurerm_storage_account.rxetl.primary_connection_string,
    "FUNC_TASK_SIGNAL_QUEUE_CONN_STR" = azurerm_storage_account.rxetl.primary_connection_string,
    "FUNC_OPERATIONS_QUEUE_CONN_STR"  = azurerm_storage_account.rxetl.primary_connection_string,

    # Executor settings #######################################################

    ## Azure Storage

    ### Queues
    "PCTASKS_EXEC__NOTIFICATION_QUEUE__CONNECTION_STRING" = azurerm_storage_account.rxetl.primary_connection_string,
    "PCTASKS_EXEC__INBOX_QUEUE__CONNECTION_STRING"        = azurerm_storage_account.rxetl.primary_connection_string,
    "PCTASKS_EXEC__SIGNAL_QUEUE__CONNECTION_STRING"       = azurerm_storage_account.rxetl.primary_connection_string,
    "PCTASKS_EXEC__SIGNAL_QUEUE_ACCOUNT_NAME"             = azurerm_storage_account.rxetl.name,
    "PCTASKS_EXEC__SIGNAL_QUEUE_ACCOUNT_KEY"              = azurerm_storage_account.rxetl.primary_access_key,

    ### Tables
    "PCTASKS_EXEC__TABLES_ACCOUNT_URL"  = azurerm_storage_account.rxetl.primary_table_endpoint,
    "PCTASKS_EXEC__TABLES_ACCOUNT_NAME" = azurerm_storage_account.rxetl.name,
    "PCTASKS_EXEC__TABLES_ACCOUNT_KEY"  = azurerm_storage_account.rxetl.primary_access_key,

    ### Blobs
    "PCTASKS_EXEC__BLOB_ACCOUNT_URL"  = azurerm_storage_account.rxetl.primary_blob_endpoint,
    "PCTASKS_EXEC__BLOB_ACCOUNT_NAME" = azurerm_storage_account.rxetl.name,
    "PCTASKS_EXEC__BLOB_ACCOUNT_KEY"  = azurerm_storage_account.rxetl.primary_access_key,

    ## Azure Batch
    "PCTASKS_EXEC__BATCH_URL"             = "https://${azurerm_batch_account.rxetl.account_endpoint}",
    "PCTASKS_EXEC__BATCH_NAME"            = azurerm_batch_account.rxetl.name,
    "PCTASKS_EXEC__BATCH_KEY"             = azurerm_batch_account.rxetl.primary_access_key,
    "PCTASKS_EXEC__BATCH_DEFAULT_POOL_ID" = var.batch_pool_id,

    ##  KeyVault
    "PCTASKS_EXEC__KEYVAULT_URL" = azurerm_key_vault.rxetl.vault_uri,

    # Router settings ##############################################################

    ## Azure Storage

    ### Queues
    "PCTASKS_ROUTER__QUEUES_CONNECTION_STRING" = azurerm_storage_account.rxetl.primary_connection_string,

    ### Tables
    "PCTASKS_ROUTER__TABLES_ACCOUNT_URL"  = azurerm_storage_account.rxetl.primary_table_endpoint,
    "PCTASKS_ROUTER__TABLES_ACCOUNT_NAME" = azurerm_storage_account.rxetl.name,
    "PCTASKS_ROUTER__TABLES_ACCOUNT_KEY"  = azurerm_batch_account.rxetl.primary_access_key,

    # Notifications settings #######################################################

    ## Azure Storage

    ### Tables
    "PCTASKS_NOTIFICATIONS__TABLES_ACCOUNT_URL"  = azurerm_storage_account.rxetl.primary_table_endpoint,
    "PCTASKS_NOTIFICATIONS__TABLES_ACCOUNT_NAME" = azurerm_storage_account.rxetl.name,
    "PCTASKS_NOTIFICATIONS__TABLES_ACCOUNT_KEY"  = azurerm_batch_account.rxetl.primary_access_key,

    # Operations settings #######################################################

    ## Azure Storage

    ### Tables

    "PCTASKS_OPS__TABLES_ACCOUNT_URL"  = azurerm_storage_account.rxetl.primary_table_endpoint,
    "PCTASKS_OPS__TABLES_ACCOUNT_NAME" = azurerm_storage_account.rxetl.name,
    "PCTASKS_OPS__TABLES_ACCOUNT_KEY"  = azurerm_batch_account.rxetl.primary_access_key,
  }

  os_type = "linux"
  version = "~4"
  site_config {
    linux_fx_version          = "PYTHON|3.8"
    use_32_bit_worker_process = false
  }
}
