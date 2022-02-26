module "resources" {
  source = "../resources"

  environment           = var.username
  region                = var.region

  batch_pool_id = var.batch_pool_id

  task_acr_name = var.task_acr_name
  acr_sp_client_id = var.acr_sp_client_id
  acr_sp_client_secret = var.acr_sp_client_secret
  acr_sp_object_id = var.acr_sp_object_id

  task_sp_tenant_id = var.task_sp_tenant_id
  task_sp_client_id = var.task_sp_client_id
  task_sp_client_secret = var.task_sp_client_secret

  db_username =  var.db_username
  db_password = var.db_password

  db_storage_mb = var.db_storage_mb
}