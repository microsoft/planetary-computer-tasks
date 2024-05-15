resource "azurerm_kubernetes_cluster" "pctasks" {
  name                = "aks-${local.prefix}"
  location            = azurerm_resource_group.pctasks.location
  resource_group_name = azurerm_resource_group.pctasks.name
  dns_prefix          = "${local.prefix}-cluster"
  # kubernetes_version  = var.k8s_version

  oms_agent {
    log_analytics_workspace_id = azurerm_log_analytics_workspace.pctasks.id
  }

  # https://learn.microsoft.com/en-us/azure/aks/auto-upgrade-cluster#use-cluster-auto-upgrade
  automatic_channel_upgrade = "rapid"

  # https://learn.microsoft.com/en-us/azure/aks/auto-upgrade-node-os-image
  node_os_channel_upgrade = "NodeImage"

  image_cleaner_enabled = true

  default_node_pool {
    name           = "agentpool"
    vm_size        = "Standard_DS2_v2"
    os_sku         = "AzureLinux"
    node_count     = var.aks_node_count
    vnet_subnet_id = azurerm_subnet.k8snode_subnet.id

    node_labels = {
      node_group = "default"
    }

    temporary_name_for_rotation = "tmpdefault"
  }

  identity {
    type = "SystemAssigned"
  }

  azure_active_directory_role_based_access_control {
    managed            = true
    azure_rbac_enabled = true
  }

  workload_identity_enabled = true
  oidc_issuer_enabled       = true

  tags = {
    Environment = var.environment
    ManagedBy   = "AI4E"
  }
}

resource "azurerm_kubernetes_cluster_node_pool" "argowf" {
  name                  = "argowf"
  kubernetes_cluster_id = azurerm_kubernetes_cluster.pctasks.id
  vm_size               = "Standard_DS2_v2"
  os_sku                = "AzureLinux"
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
  vm_size               = "Standard_D3_v2"
  os_sku                = "AzureLinux"
  enable_auto_scaling   = true
  min_count             = var.aks_task_pool_min_count
  max_count             = var.aks_task_pool_max_count

  node_labels = {
    node_group = var.aks_streaming_task_node_group_name
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

# Node pool *with spot instances* for running tasks.
resource "azurerm_kubernetes_cluster_node_pool" "tasks-spot" {
  name                  = "tasksspot"
  kubernetes_cluster_id = azurerm_kubernetes_cluster.pctasks.id
  vm_size               = "Standard_D3_v2"
  os_sku                = "AzureLinux"
  enable_auto_scaling   = true
  min_count             = var.aks_task_pool_min_count
  max_count             = var.aks_task_pool_max_count

  # Spot configuration
  priority        = "Spot"
  eviction_policy = "Delete"
  spot_max_price  = -1

  node_labels = {
    node_group                              = var.aks_streaming_task_node_group_name
    "kubernetes.azure.com/scalesetpriority" = "spot"
  }
  node_taints = [
    "kubernetes.azure.com/scalesetpriority=spot:NoSchedule",
  ]

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

# Identity to be use in Argo Workflow pods. Ensure the service account used below
# Is the same associated with pod pod deployment.
resource "azurerm_user_assigned_identity" "workflows" {
  name                = "id-${local.prefix}-workflows"
  location            = var.region
  resource_group_name = azurerm_resource_group.pctasks.name
}

resource "azurerm_federated_identity_credential" "workflows" {
  name                = "federated-id-${local.prefix}-workflows"
  resource_group_name = azurerm_resource_group.pctasks.name
  audience            = ["api://AzureADTokenExchange"]
  issuer              = azurerm_kubernetes_cluster.pctasks.oidc_issuer_url
  subject             = "system:serviceaccount:pc:${var.aks_pctasks_service_account}"
  parent_id           = azurerm_user_assigned_identity.workflows.id
  timeouts {}
}
