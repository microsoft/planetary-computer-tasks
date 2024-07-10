resource "azurerm_batch_pool" "batch_pool" {

  name                = var.name
  metadata            = {}
  resource_group_name = var.resource_group_name
  account_name        = var.account_name
  display_name        = var.display_name
  vm_size             = var.vm_size
  max_tasks_per_node  = var.max_tasks_per_node

  inter_node_communication = "Disabled"

  identity {
    type         = "UserAssigned"
    identity_ids = [var.user_assigned_identity_id]
  }

  network_configuration {
    subnet_id = var.subnet_id
    public_ips = []

  }

  task_scheduling_policy {
    node_fill_type = "Spread"
  }

  # Simplified communication mode is compatible with the NSG policies
  # on our vnet.
  target_node_communication_mode = "Simplified"

  container_configuration {
    type = "DockerCompatible"
    container_registries {
      registry_server           = "${var.acr_name}.azurecr.io"
      user_assigned_identity_id = var.user_assigned_identity_id
    }
  }

  node_agent_sku_id = "batch.node.ubuntu 20.04"

  storage_image_reference {
    publisher = "microsoft-azure-batch"
    offer     = "ubuntu-server-container"
    sku       = "20-04-lts"
    version   = "latest"
  }

  auto_scale {
    evaluation_interval = "PT5M"

    formula = <<EOF
      maxTasksPerNode = ${var.max_tasks_per_node};

      minTargetDedicated = ${var.min_dedicated};
      maxTargetDedicated = ${var.max_dedicated};
      minTargetLowPriority = ${var.min_low_priority};
      maxTargetLowPriority = ${var.max_low_priority};

      maxIncreasePerScale = ${var.max_increase_per_scale};

      preempted = max(0, $PreemptedNodeCount.GetSample(1));

      tasks = max(0, $PendingTasks.GetSample(1));
      taskNodes = (tasks + maxTasksPerNode - 1) / maxTasksPerNode;
      lowPriorityTasks = min(taskNodes, maxTargetLowPriority + preempted);

      desiredLowPriorityNodes = max(minTargetLowPriority, lowPriorityTasks);
      lowPriorityNodesToAdd = desiredLowPriorityNodes - $CurrentLowPriorityNodes;
      actualChange = min(lowPriorityNodesToAdd, maxIncreasePerScale);

      $TargetLowPriorityNodes = max(0, $CurrentLowPriorityNodes + actualChange);

      tasksLeft = taskNodes - $TargetLowPriorityNodes;
      $TargetDedicatedNodes = max(minTargetDedicated, min(tasksLeft, maxTargetDedicated));

      $NodeDeallocationOption = taskcompletion;
    EOF

  }
}

