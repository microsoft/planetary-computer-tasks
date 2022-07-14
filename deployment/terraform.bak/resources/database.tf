data "http" "ip" {
  url = "https://ifconfig.me"
}

resource "azurerm_postgresql_flexible_server" "db" {
  name                = "${local.prefix}-stacdb"
  location            = azurerm_resource_group.rxetl.location
  resource_group_name = azurerm_resource_group.rxetl.name

  sku_name = "GP_Standard_D4s_v3"

  storage_mb            = var.db_storage_mb
  backup_retention_days = 7

  administrator_login    = var.db_username
  administrator_password = var.db_password
  version                = "13"
  zone                   = 1
}

resource "azurerm_postgresql_flexible_server_database" "postgis" {
  name      = "postgis"
  server_id = azurerm_postgresql_flexible_server.db.id
  charset   = "utf8"
  collation = "en_US.utf8"
}

resource "azurerm_postgresql_flexible_server_firewall_rule" "deployer_ip" {
  name             = "terraform-user-access-fw"
  server_id        = azurerm_postgresql_flexible_server.db.id
  start_ip_address = data.http.ip.body
  end_ip_address   = data.http.ip.body

}