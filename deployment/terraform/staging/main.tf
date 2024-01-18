module "resources" {
  source = "../resources"

  environment = "staging"
  region      = "West Europe"

  pctasks_server_image_tag = "latest"
  pctasks_run_image_tag    = "latest"

  batch_default_pool_id = var.batch_default_pool_id

  task_acr_resource_group      = var.task_acr_resource_group
  task_acr_name                = var.task_acr_name
  task_acr_sp_object_id        = var.task_acr_sp_object_id
  component_acr_resource_group = var.component_acr_resource_group
  component_acr_name           = var.component_acr_name

  task_sp_tenant_id     = var.task_sp_tenant_id
  task_sp_object_id     = var.task_sp_object_id
  task_sp_client_id     = var.task_sp_client_id
  task_sp_client_secret = var.task_sp_client_secret

  pctasks_task_kv = "kv-pctaskstest-staging"
  # Note: this resource group is managed by terraform but contains the manually managed keyvault
  pctasks_task_kv_resource_group_name = "rg-pctaskstest-staging-westeurope"

  kv_sp_tenant_id     = var.kv_sp_tenant_id
  kv_sp_object_id     = var.kv_sp_object_id
  kv_sp_client_id     = var.kv_sp_client_id
  kv_sp_client_secret = var.kv_sp_client_secret

  deploy_secrets_kv_name         = var.deploy_secrets_kv_name
  deploy_secrets_kv_rg           = var.deploy_secrets_kv_rg
  access_key_secret_name         = var.access_key_secret_name
  backend_api_app_id_secret_name = var.backend_api_app_id_secret_name

  pctasks_server_sp_tenant_id     = var.pctasks_server_sp_tenant_id
  pctasks_server_sp_client_id     = var.pctasks_server_sp_client_id
  pctasks_server_sp_client_secret = var.pctasks_server_sp_client_secret
  pctasks_server_sp_object_id     = var.pctasks_server_sp_object_id

  streaming_taskio_sp_tenant_id     = var.streaming_taskio_sp_tenant_id
  streaming_taskio_sp_client_id     = var.streaming_taskio_sp_client_id
  streaming_taskio_sp_client_secret = var.streaming_taskio_sp_client_secret
  streaming_taskio_sp_object_id     = var.streaming_taskio_sp_object_id

  k8s_version              = "1.26.6"
  k8s_orchestrator_version = "1.26.6"

  stac_db_connection_string = var.stac_db_connection_string

  cosmosdb_account_name   = var.cosmosdb_account_name
  cosmosdb_resource_group = var.cosmosdb_resource_group

  cluster_cert_issuer          = "letsencrypt"
  cluster_cert_server          = "https://acme-v02.api.letsencrypt.org/directory"
  aks_node_count               = 2
  pctasks_server_replica_count = 1
  apim_sku_name                = var.apim_sku_name
}
