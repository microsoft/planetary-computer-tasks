
resource "azurerm_app_service_plan" "pctasks" {
  name                = "plan-${local.prefix}"
  location            = azurerm_resource_group.pctasks.location
  resource_group_name = azurerm_resource_group.pctasks.name
  kind                = "functionapp"
  reserved            = true

  sku {
    tier = "Dynamic"
    size = "Y1"
  }
}

resource "azurerm_function_app" "pctasks" {
  name                       = "func-${local.prefix}"
  location                   = azurerm_resource_group.pctasks.location
  resource_group_name        = azurerm_resource_group.pctasks.name
  app_service_plan_id        = azurerm_app_service_plan.pctasks.id
  storage_account_name       = azurerm_storage_account.pctasks.name
  storage_account_access_key = azurerm_storage_account.pctasks.primary_access_key
  https_only                 = true

  identity {
    type = "SystemAssigned"
  }

  app_settings = {
    # TODO: Clean up function environment to remove unused.

    "ENABLE_ORYX_BUILD"                  = "true",
    "SCM_DO_BUILD_DURING_DEPLOYMENT"     = "true",
    "FUNCTIONS_WORKER_RUNTIME"           = "python",
    "APP_INSIGHTS_IKEY"                  = azurerm_application_insights.pctasks.instrumentation_key,
    "APPINSIGHTS_INSTRUMENTATIONKEY"     = azurerm_application_insights.pctasks.instrumentation_key,
    "AzureStorageQueuesConnectionString" = azurerm_storage_account.pctasks.primary_connection_string,
    "AzureWebJobsDisableHomepage"        = true,

    # Function queue trigger bindings ##
    "FUNC_NOTIFY_QUEUE_CONN_STR"      = azurerm_storage_account.pctasks.primary_connection_string,
    "FUNC_ROUTER_QUEUE_CONN_STR"      = azurerm_storage_account.pctasks.primary_connection_string,
    "FUNC_WORKFLOW_QUEUE_CONN_STR"    = azurerm_storage_account.pctasks.primary_connection_string,
    "FUNC_TASKS_QUEUE_CONN_STR"       = azurerm_storage_account.pctasks.primary_connection_string,
    "FUNC_TASK_SIGNAL_QUEUE_CONN_STR" = azurerm_storage_account.pctasks.primary_connection_string,
    "FUNC_OPERATIONS_QUEUE_CONN_STR"  = azurerm_storage_account.pctasks.primary_connection_string,

    # PCTasks Server settings #######################################################

    "PCTASKS_SERVER_URL"         = "https://${azurerm_public_ip.pctasks.domain_name_label}.${local.location}.cloudapp.azure.com/tasks"

    # Executor settings #######################################################

    ## Azure Storage

    ### Queues
    "PCTASKS_RUN__NOTIFICATION_QUEUE__CONNECTION_STRING" = azurerm_storage_account.pctasks.primary_connection_string,
    "PCTASKS_RUN__INBOX_QUEUE__CONNECTION_STRING"        = azurerm_storage_account.pctasks.primary_connection_string,
    "PCTASKS_RUN__SIGNAL_QUEUE__CONNECTION_STRING"       = azurerm_storage_account.pctasks.primary_connection_string,
    "PCTASKS_RUN__SIGNAL_QUEUE_ACCOUNT_NAME"             = azurerm_storage_account.pctasks.name,
    "PCTASKS_RUN__SIGNAL_QUEUE_ACCOUNT_KEY"              = azurerm_storage_account.pctasks.primary_access_key,

    ### Tables
    "PCTASKS_RUN__TABLES_ACCOUNT_URL"  = azurerm_storage_account.pctasks.primary_table_endpoint,
    "PCTASKS_RUN__TABLES_ACCOUNT_NAME" = azurerm_storage_account.pctasks.name,
    "PCTASKS_RUN__TABLES_ACCOUNT_KEY"  = azurerm_storage_account.pctasks.primary_access_key,

    ### Blobs
    "PCTASKS_RUN__BLOB_ACCOUNT_URL"  = azurerm_storage_account.pctasks.primary_blob_endpoint,
    "PCTASKS_RUN__BLOB_ACCOUNT_NAME" = azurerm_storage_account.pctasks.name,
    "PCTASKS_RUN__BLOB_ACCOUNT_KEY"  = azurerm_storage_account.pctasks.primary_access_key,

    ## Azure Batch
    "PCTASKS_RUN__BATCH_URL"             = "https://${azurerm_batch_account.pctasks.account_endpoint}",
    "PCTASKS_RUN__BATCH_NAME"            = azurerm_batch_account.pctasks.name,
    "PCTASKS_RUN__BATCH_KEY"             = azurerm_batch_account.pctasks.primary_access_key,
    "PCTASKS_RUN__BATCH_DEFAULT_POOL_ID" = var.batch_default_pool_id,

    ##  KeyVault
    "PCTASKS_RUN__KEYVAULT_URL" = data.azurerm_key_vault.pctasks.vault_uri,

    # Router settings ##############################################################

    ## Azure Storage

    ### Queues
    "PCTASKS_ROUTER__QUEUES_CONNECTION_STRING" = azurerm_storage_account.pctasks.primary_connection_string,

    ### Tables
    "PCTASKS_ROUTER__TABLES_ACCOUNT_URL"  = azurerm_storage_account.pctasks.primary_table_endpoint,
    "PCTASKS_ROUTER__TABLES_ACCOUNT_NAME" = azurerm_storage_account.pctasks.name,
    "PCTASKS_ROUTER__TABLES_ACCOUNT_KEY"  = azurerm_batch_account.pctasks.primary_access_key,

    # Notifications settings #######################################################

    ## Azure Storage

    ### Tables
    "PCTASKS_NOTIFICATIONS__TABLES_ACCOUNT_URL"  = azurerm_storage_account.pctasks.primary_table_endpoint,
    "PCTASKS_NOTIFICATIONS__TABLES_ACCOUNT_NAME" = azurerm_storage_account.pctasks.name,
    "PCTASKS_NOTIFICATIONS__TABLES_ACCOUNT_KEY"  = azurerm_batch_account.pctasks.primary_access_key,

    # Operations settings #######################################################

    ## Azure Storage

    ### Tables

    "PCTASKS_OPS__TABLES_ACCOUNT_URL"  = azurerm_storage_account.pctasks.primary_table_endpoint,
    "PCTASKS_OPS__TABLES_ACCOUNT_NAME" = azurerm_storage_account.pctasks.name,
    "PCTASKS_OPS__TABLES_ACCOUNT_KEY"  = azurerm_batch_account.pctasks.primary_access_key,
  }

  os_type = "linux"
  version = "~4"
  site_config {
    linux_fx_version          = "PYTHON|3.8"
    use_32_bit_worker_process = false
  }
}
