resource "azurerm_storage_account" "pctasks" {
  name                            = local.nodash_prefix
  resource_group_name             = azurerm_resource_group.pctasks.name
  location                        = azurerm_resource_group.pctasks.location
  account_tier                    = "Standard"
  account_replication_type        = "LRS"
  allow_nested_items_to_be_public = false
}

# Tables

resource "azurerm_storage_table" "imagekeys" {
  name                 = "imagekeys"
  storage_account_name = azurerm_storage_account.pctasks.name
}

# Blob

resource "azurerm_storage_container" "tasklogs" {
  name                  = "tasklogs"
  storage_account_name  = azurerm_storage_account.pctasks.name
  container_access_type = "private"
}

resource "azurerm_storage_container" "taskio" {
  name                  = "taskio"
  storage_account_name  = azurerm_storage_account.pctasks.name
  container_access_type = "private"
}

resource "azurerm_storage_container" "code" {
  name                  = "code"
  storage_account_name  = azurerm_storage_account.pctasks.name
  container_access_type = "private"
}

# Queue

resource "azurerm_storage_queue" "storage-events" {
  name                 = "storage-events"
  storage_account_name = azurerm_storage_account.pctasks.name
}

resource "azurerm_storage_queue" "ingest" {
  name                 = "ingest"
  storage_account_name = azurerm_storage_account.pctasks.name
}

# Dataset Queues
resource "azurerm_storage_queue" "queues" {
  for_each = toset([
   # dataset work queues
    "goes-glm",
    "goes-cmi",
    "sentinel-1-grd",
    "sentinel-1-rtc",
    "ecmwf-forecast",
    "landsat-c2-l2",
    "modis-09a1-061",
    "modis-09q1-061",
    "modis-10a1-061",
    "modis-10a2-061",
    "modis-11a1-061",
    "modis-11a2-061",
    "modis-13a1-061",
    "modis-13q1-061",
    "modis-14a1-061",
    "modis-14a2-061",
    "modis-15a2h-061",
    "modis-15a3h-061",
    "modis-16a3gf-061",
    "modis-17a2h-061",
    "modis-17a2hgf-061",
    "modis-17a3hgf-061",
    "modis-21a2-061",
    "modis-43a4-061",
    "modis-64a1-061",
  ])
  name                 = each.key
  storage_account_name = azurerm_storage_account.pctasks.name
}

# Access Policies
# These require Owner or User Access Administrator permissions on the
# the storage account.

resource "azurerm_role_assignment" "pctasks-server-blob-access" {
  scope                = azurerm_storage_account.pctasks.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = var.pctasks_server_sp_object_id
}

resource "azurerm_role_assignment" "pctasks-server-queue-access" {
  scope                = azurerm_storage_account.pctasks.id
  role_definition_name = "Storage Queue Data Contributor"
  principal_id         = var.pctasks_server_sp_object_id
}

resource "azurerm_role_assignment" "pctasks-server-table-access" {
  scope                = azurerm_storage_account.pctasks.id
  role_definition_name = "Storage Table Data Contributor"
  principal_id         = var.pctasks_server_sp_object_id
}

# Let the Azure Functions in pctasks process queue messages.
resource "azurerm_role_assignment" "pctasks-functions-queue-access" {
  scope                = azurerm_storage_account.pctasks.id
  role_definition_name = "Storage Queue Data Contributor"
  principal_id         = azurerm_linux_function_app.pctasks.identity[0].principal_id
}

# The Task Service Principal should be able to process queue messages
# for the dataset work queues
resource "azurerm_role_assignment" "pctasks-task-queue-access" {
  scope                = azurerm_storage_account.pctasks.id
  role_definition_name = "Storage Queue Data Contributor"
  principal_id         = var.task_sp_object_id
}

resource "azurerm_role_assignment" "pctasks-taskio-blob-access" {
  scope                = azurerm_storage_account.pctasks.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = var.streaming_taskio_sp_object_id
}