module "resources" {
  source = "../resources"

  environment = "staging"
  region = "West Europe"

  batch_default_pool_id = var.batch_default_pool_id

  task_acr_resource_group = var.task_acr_resource_group
  task_acr_name = var.task_acr_name
  task_acr_sp_object_id = var.task_acr_sp_object_id
  component_acr_resource_group = var.component_acr_resource_group
  component_acr_name = var.component_acr_name

  task_sp_tenant_id = var.task_sp_tenant_id
  task_sp_client_id = var.task_sp_client_id
  task_sp_client_secret = var.task_sp_client_secret

  kv_sp_tenant_id = var.kv_sp_tenant_id
  kv_sp_client_id = var.kv_sp_client_id
  kv_sp_client_secret = var.kv_sp_client_secret

  pctasks_server_sp_tenant_id = var.pctasks_server_sp_tenant_id
  pctasks_server_sp_client_id = var.pctasks_server_sp_client_id
  pctasks_server_sp_client_secret = var.pctasks_server_sp_client_secret
  pctasks_server_sp_object_id = var.pctasks_server_sp_object_id

  k8s_version = "1.23.5"
  k8s_orchestrator_version = "1.23.5"

  stac_db_connection_string =  var.stac_db_connection_string

  pctasks_server_account_key = var.pctasks_server_account_key

  cluster_cert_issuer = "letsencrypt"
  cluster_cert_server = "https://acme-v02.api.letsencrypt.org/directory"
  aks_node_count = 1
  pctasks_server_replica_count = 1
}