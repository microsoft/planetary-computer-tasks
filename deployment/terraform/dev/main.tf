module "resources" {
  source = "../resources"

  environment           = "dev"
  region                = var.region

  pctasks_server_image_tag = var.pctasks_server_image_tag
  pctasks_run_image_tag = var.pctasks_run_image_tag

  batch_default_pool_id = var.batch_default_pool_id

  task_acr_resource_group = var.task_acr_resource_group
  task_acr_name = var.task_acr_name
  task_acr_sp_object_id = var.task_acr_sp_object_id
  component_acr_resource_group = var.component_acr_resource_group
  component_acr_name = var.component_acr_name

  pctasks_task_kv = var.pctasks_task_kv
  pctasks_task_kv_resource_group_name = var.pctasks_task_kv_resource_group_name

  deploy_secrets_kv_name = var.deploy_secrets_kv_name
  deploy_secrets_kv_rg = var.deploy_secrets_kv_rg
  access_key_secret_name = var.access_key_secret_name
  backend_api_app_id_secret_name = var.backend_api_app_id_secret_name

  k8s_version = "1.26.3"
  k8s_orchestrator_version = "1.26.3"

  stac_db_connection_string =  var.stac_db_connection_string

  cosmosdb_account_name = var.cosmosdb_account_name
  cosmosdb_resource_group = var.cosmosdb_resource_group

  cluster_cert_issuer = "letsencrypt"
  cluster_cert_server = "https://acme-v02.api.letsencrypt.org/directory"
  aks_node_count = 1
  pctasks_server_replica_count = 1
  apim_sku_name = var.apim_sku_name
}
