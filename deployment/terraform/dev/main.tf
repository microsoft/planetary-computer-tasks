module "resources" {
  source = "../resources"

  environment           = var.username
  region                = var.region

  pctasks_server_image_tag = "rob"
  pctasks_run_image_tag = "rob"

  batch_default_pool_id = var.batch_default_pool_id

  task_acr_resource_group = var.task_acr_resource_group
  task_acr_name = var.task_acr_name
  task_acr_sp_object_id = var.task_acr_sp_object_id
  component_acr_resource_group = var.component_acr_resource_group
  component_acr_name = var.component_acr_name

  task_sp_tenant_id = var.task_sp_tenant_id
  task_sp_client_id = var.task_sp_client_id
  task_sp_client_secret = var.task_sp_client_secret

  pctasks_test_kv = "kv-pctaskstest-rob"
  # Note: this resource group is managed by terraform but contains the manually managed keyvault
  pctasks_test_kv_resource_group_name = "rg-pctaskstest-rob-westeurope"

  kv_sp_tenant_id = var.kv_sp_tenant_id
  kv_sp_client_id = var.kv_sp_client_id
  kv_sp_client_secret = var.kv_sp_client_secret

  deploy_secrets_kv_name = var.deploy_secrets_kv_name
  deploy_secrets_kv_rg = var.deploy_secrets_kv_rg
  access_key_secret_name = var.access_key_secret_name
  backend_api_app_id_secret_name = var.backend_api_app_id_secret_name

  pctasks_server_sp_tenant_id = var.pctasks_server_sp_tenant_id
  pctasks_server_sp_client_id = var.pctasks_server_sp_client_id
  pctasks_server_sp_client_secret = var.pctasks_server_sp_client_secret
  pctasks_server_sp_object_id = var.pctasks_server_sp_object_id

  k8s_version = "1.23.5"
  k8s_orchestrator_version = "1.23.5"

  stac_db_connection_string =  var.stac_db_connection_string

  cosmosdb_account_name = "cdb-pctaskstest-rob"
  cosmosdb_resource_group = "rg-pctaskstest-rob-westeurope"

  cluster_cert_issuer = "letsencrypt"
  cluster_cert_server = "https://acme-v02.api.letsencrypt.org/directory"
  aks_node_count = 1
  pctasks_server_replica_count = 1
}
