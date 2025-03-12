resource "azurerm_virtual_network" "pctasks" {
  name                = "vnet-${local.prefix}"
  location            = azurerm_resource_group.pctasks.location
  resource_group_name = azurerm_resource_group.pctasks.name
  address_space       = ["10.0.0.0/8"]
}

resource "azurerm_network_security_group" "pctasks" {
  name                = "nsg-${local.prefix}"
  location            = azurerm_resource_group.pctasks.location
  resource_group_name = azurerm_resource_group.pctasks.name
}

resource "azurerm_network_security_rule" "ingress" {
  name                       = "nsg-rule"
  priority                   = 100
  direction                  = "Inbound"
  access                     = "Allow"
  protocol                   = "Tcp"
  source_port_range          = "*"
  destination_port_ranges    = [80, 443, 3443, 29876, 29877]
  source_address_prefix      = "*"
  destination_address_prefix = "*"

  network_security_group_name = azurerm_network_security_group.pctasks.name
  resource_group_name         = azurerm_resource_group.pctasks.name
}

resource "azurerm_network_security_rule" "batch-inbound" {
  name                       = "batch-inbound"
  priority                   = 110
  direction                  = "Inbound"
  access                     = "Allow"
  protocol                   = "Tcp"
  source_port_range          = "*"
  destination_port_range     = "29876-29877"
  source_address_prefix      = "BatchNodeManagement.WestEurope"
  destination_address_prefix = "*"

  network_security_group_name = azurerm_network_security_group.pctasks.name
  resource_group_name         = azurerm_resource_group.pctasks.name
}

resource "azurerm_network_security_rule" "batch-outbound" {
  name                       = "batch-outbound"
  priority                   = 111
  direction                  = "Outbound"
  access                     = "Allow"
  protocol                   = "Tcp"
  source_port_range          = "*"
  destination_port_range     = "443"
  source_address_prefix      = "Storage.WestEurope"
  destination_address_prefix = "*"

  network_security_group_name = azurerm_network_security_group.pctasks.name
  resource_group_name         = azurerm_resource_group.pctasks.name
}

# Batch pool subnet

resource "azurerm_subnet" "nodepool_subnet" {
  name                 = "snet-${local.prefix}-batch"
  virtual_network_name = azurerm_virtual_network.pctasks.name
  resource_group_name  = azurerm_resource_group.pctasks.name
  address_prefixes     = ["10.1.0.0/16"]
  service_endpoints    = ["Microsoft.Sql", "Microsoft.KeyVault", "Microsoft.ContainerRegistry", "Microsoft.AzureCosmosDB", "Microsoft.Storage"]
}

resource "azurerm_subnet_network_security_group_association" "nodepool_subnet" {
  subnet_id                 = azurerm_subnet.nodepool_subnet.id
  network_security_group_id = azurerm_network_security_group.pctasks.id
}

# AKS node subnet

resource "azurerm_subnet" "k8snode_subnet" {
  name                 = "snet-${local.prefix}-k8s"
  virtual_network_name = azurerm_virtual_network.pctasks.name
  resource_group_name  = azurerm_resource_group.pctasks.name
  address_prefixes     = ["10.2.0.0/16"]
  service_endpoints = [
    "Microsoft.Sql",
    "Microsoft.Storage",
    "Microsoft.KeyVault",
    "Microsoft.ContainerRegistry",
    "Microsoft.AzureCosmosDB",
    "Microsoft.Storage"
  ]
}

resource "azurerm_subnet_network_security_group_association" "k8snode_subnet" {
  subnet_id                 = azurerm_subnet.k8snode_subnet.id
  network_security_group_id = azurerm_network_security_group.pctasks.id
}

# APIM node subnet

resource "azurerm_subnet" "apim_subnet" {
  name                 = "snet-${local.prefix}-apim"
  virtual_network_name = azurerm_virtual_network.pctasks.name
  resource_group_name  = azurerm_resource_group.pctasks.name
  address_prefixes     = ["10.4.0.0/16"]
  service_endpoints    = ["Microsoft.Storage"]
}

resource "azurerm_subnet_network_security_group_association" "apim_subnet" {
  subnet_id                 = azurerm_subnet.apim_subnet.id
  network_security_group_id = azurerm_network_security_group.pctasks.id
}

# Function subnet


resource "azurerm_subnet" "function_subnet" {
  name                 = "${local.prefix}-functions-subnet"
  virtual_network_name = azurerm_virtual_network.pctasks.name
  resource_group_name  = azurerm_resource_group.pctasks.name

  service_endpoints = ["Microsoft.Storage.Global"]
  delegation {
    name = "delegation"
    service_delegation {
      actions = [
        "Microsoft.Network/virtualNetworks/subnets/action",
      ]
      name = "Microsoft.Web/serverFarms"
    }
  }

  address_prefixes = ["10.3.0.0/26"]
}
