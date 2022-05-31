resource "azurerm_virtual_network" "rxetl" {
  name                = "${local.prefix}-network"
  location            = azurerm_resource_group.rxetl.location
  resource_group_name = azurerm_resource_group.rxetl.name
  address_space       = ["10.0.0.0/8"]
}

resource "azurerm_subnet" "nodepool_subnet" {
  name                 = "${local.prefix}-pool-subnet"
  virtual_network_name = azurerm_virtual_network.rxetl.name
  resource_group_name  = azurerm_resource_group.rxetl.name
  address_prefixes     = ["10.1.0.0/16"]
  service_endpoints = ["Microsoft.Sql", "Microsoft.KeyVault", "Microsoft.ContainerRegistry", "Microsoft.AzureCosmosDB"]
}

resource "azurerm_network_security_group" "rxetl" {
  name                = "${local.prefix}-security-group"
  location            = azurerm_resource_group.rxetl.location
  resource_group_name = azurerm_resource_group.rxetl.name

  security_rule {
    name                       = "nsg-rule"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "*"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }
}


resource "azurerm_subnet" "k8snode_subnet" {
  name                 = "${local.prefix}-node-subnet"
  virtual_network_name = azurerm_virtual_network.rxetl.name
  resource_group_name  = azurerm_resource_group.rxetl.name
  address_prefixes     = ["10.1.0.0/16"]
  service_endpoints = [
    "Microsoft.Sql",
    "Microsoft.Storage",
    "Microsoft.KeyVault",
    "Microsoft.ContainerRegistry",
  ]
}

resource "azurerm_subnet_network_security_group_association" "rxetl" {
  subnet_id                 = azurerm_subnet.nodepool_subnet.id
  network_security_group_id = azurerm_network_security_group.rxetl.id
}