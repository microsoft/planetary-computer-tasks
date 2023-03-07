resource "azurerm_kubernetes_cluster" "pctasks" {
  name                = "aks-${local.prefix}"
  location            = azurerm_resource_group.pctasks.location
  resource_group_name = azurerm_resource_group.pctasks.name
  dns_prefix          = "${local.prefix}-cluster"
  kubernetes_version  = var.k8s_version



  default_node_pool {
    name                 = "agentpool"
    vm_size              = "Standard_DS2_v2"
    node_count           = var.aks_node_count
    vnet_subnet_id       = azurerm_subnet.k8snode_subnet.id

    node_labels = {
      node_group = "default"
    }
  }

  identity {
    type = "SystemAssigned"
  }

  azure_active_directory_role_based_access_control {
    managed            = true
    azure_rbac_enabled = true
  }

  tags = {
    Environment = var.environment
    ManagedBy   = "AI4E"
  }
}

resource "azurerm_kubernetes_cluster_node_pool" "argowf" {
  name                  = "argowf"
  kubernetes_cluster_id = azurerm_kubernetes_cluster.pctasks.id
  vm_size               = "Standard_DS2_v2"
  node_count            = 1

  node_labels = {
    node_group = var.argo_wf_node_group_name
  }

   lifecycle {
    ignore_changes = [
      # Ignore changes that are auto-populated by AKS
      vnet_subnet_id,
      node_taints,
      zones,
    ]
  }

  tags = {
    Environment = var.environment
    ManagedBy   = "AI4E"
  }
}

# Node pool for running tasks
resource "azurerm_kubernetes_cluster_node_pool" "tasks" {
  name                  = "tasks"
  kubernetes_cluster_id = azurerm_kubernetes_cluster.pctasks.id
  vm_size               = "Standard_D16d_v4"
  enable_auto_scaling = true
  min_count = 0
  max_count = var.aks_task_pool_max_count

  node_labels = {
    # this should match the value in pctasks
    node_group = "pc-lowlatency"
  }

   lifecycle {
    ignore_changes = [
      # Ignore changes that are auto-populated by AKS
      vnet_subnet_id,
      node_taints,
      zones,
      node_count,
    ]
  }

  tags = {
    Environment = var.environment
    ManagedBy   = "AI4E"
  }
}


# add the role to the identity the kubernetes cluster was assigned
resource "azurerm_role_assignment" "network" {
  scope                = azurerm_resource_group.pctasks.id
  role_definition_name = "Network Contributor"
  principal_id         = azurerm_kubernetes_cluster.pctasks.identity[0].principal_id
}


# Kubernetes namespace for running low-latency tasks.
# All the secrets and trigger authentications needed by KEDA must be set in this namespace.
resource "kubernetes_namespace" "tasks" {
  metadata {
    name = "tasks"
  }
}


# Kubernetes secret for KEDA to monitor storage queues.
# This is used in the KEDA TriggerAuthentication created during deployment.
resource "kubernetes_secret" "queue_connection_string" {
  metadata {
    # Note: this must match the name inn keda-trigger-authentication.yaml
    name = "secrets-storage-queue-connection-string"
    namespace = "tasks"
  }

  data = {
    ConnectionString = azurerm_storage_account.pctasks.primary_connection_string
  }

}
