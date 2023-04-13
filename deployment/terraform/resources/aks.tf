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

# add the role to the identity the kubernetes cluster was assigned
resource "azurerm_role_assignment" "network" {
  scope                = azurerm_resource_group.pctasks.id
  role_definition_name = "Network Contributor"
  principal_id         = azurerm_kubernetes_cluster.pctasks.identity[0].principal_id
}


resource "azurerm_kubernetes_cluster_node_pool" "dask" {
  name                  = "dask"
  kubernetes_cluster_id = azurerm_kubernetes_cluster.pctasks.id
  vm_size               = "Standard_E8s_v3"
  enable_auto_scaling   = true
  min_count             = 0
  max_count             = 100
  # In theory, there's no reason for the orchestrator
  # to differ from the default. But we added this node pool later,
  # after the default had shifted, so we had to specify this.
  # Next time, this can be removed.
  orchestrator_version  = "1.23.15"

  node_labels = {
    node_group = "dask"
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