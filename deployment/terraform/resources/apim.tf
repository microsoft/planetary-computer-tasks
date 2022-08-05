resource "azurerm_api_management" "pctasks" {
  name                = local.prefix
  location            = azurerm_resource_group.pctasks.location
  resource_group_name = azurerm_resource_group.pctasks.name
  publisher_name      = "Microsoft"
  publisher_email     = "planetarycomputer@microsoft.com"

  sku_name = "Standard_1"

  identity {
    type = "SystemAssigned"
  }
}

resource "azurerm_key_vault_access_policy" "apim" {
  key_vault_id = data.azurerm_key_vault.deploy_secrets.id
  tenant_id    = azurerm_api_management.pctasks.identity[0].tenant_id
  object_id    = azurerm_api_management.pctasks.identity[0].principal_id

  depends_on = [
    azurerm_api_management.pctasks,
  ]

  secret_permissions = [
    "Get", "List"
  ]
}

resource "azurerm_api_management_named_value" "pctasks_access_key" {
  name                = "pctasks-apim-access-key"
  resource_group_name = azurerm_resource_group.pctasks.name
  api_management_name = azurerm_api_management.pctasks.name
  display_name        = "pctasks-apim-access-key"
  secret              = true
  value_from_key_vault {
    secret_id = data.azurerm_key_vault_secret.access_key.id
  }
}

resource "azurerm_api_management_api" "pctasks" {
  description           = "Planetary Computer Tasks API"
  display_name          = "Planetary Computer Tasks API"
  name                  = "pctasks-api"
  protocols             = ["https"]
  api_management_name   = azurerm_api_management.pctasks.name
  resource_group_name   = azurerm_resource_group.pctasks.name
  revision              = "1"
  path                  = ""
  subscription_required = false
  subscription_key_parameter_names {
    header = "x-api-key"
    query  = "api-key"
  }
}


resource "azurerm_api_management_backend" "pctasks" {
  name                = "pctasks-backend"
  resource_group_name = azurerm_resource_group.pctasks.name
  api_management_name = azurerm_api_management.pctasks.name
  protocol            = "http"
  url                 = "https://${azurerm_public_ip.pctasks.domain_name_label}.${local.location}.cloudapp.azure.com/"
  tls {
    validate_certificate_chain = false
    validate_certificate_name  = false
  }
}

resource "azurerm_api_management_logger" "pctasks" {
  name                = "pctasks-logger"
  api_management_name = azurerm_api_management.pctasks.name
  resource_group_name = azurerm_resource_group.pctasks.name

  application_insights {
    instrumentation_key = azurerm_application_insights.pctasks.instrumentation_key
  }
}

resource "azurerm_api_management_diagnostic" "pctasks" {
  identifier               = "applicationinsights"
  resource_group_name      = azurerm_resource_group.pctasks.name
  api_management_name      = azurerm_api_management.pctasks.name
  api_management_logger_id = azurerm_api_management_logger.pctasks.id
}

resource "azurerm_api_management_api_operation" "root_head_op" {
  operation_id        = "rootheadop"
  api_name            = azurerm_api_management_api.pctasks.name
  api_management_name = azurerm_api_management.pctasks.name
  resource_group_name = azurerm_resource_group.pctasks.name
  display_name        = "Root HEAD Operation"
  method              = "HEAD"
  url_template        = "/"
  description         = "API Root HEAD Operation"
}

# The return-response policy aborts pipeline execution and returns a
# default 200 OK with no body if no other elements provided between
# the return-response tags
# HEAD operations sent to the root of the API will just return 200 OK
# so that this won't get to the backend, since there is no API designed
# for requesting root
resource "azurerm_api_management_api_operation_policy" "root_head_op_policy" {
  api_name            = azurerm_api_management_api.pctasks.name
  api_management_name = azurerm_api_management.pctasks.name
  resource_group_name = azurerm_resource_group.pctasks.name
  operation_id        = azurerm_api_management_api_operation.root_head_op.operation_id
  xml_content         = <<XML
                <policies>
                    <inbound>
                        <return-response>
                        </return-response>
                    </inbound>
                    <outbound>
                        <base />
                    </outbound>
                </policies>
                XML
}

resource "azurerm_api_management_api_operation" "tasks_get_op" {
  operation_id        = "pctasksgetop"
  api_name            = azurerm_api_management_api.pctasks.name
  api_management_name = azurerm_api_management.pctasks.name
  resource_group_name = azurerm_resource_group.pctasks.name
  display_name        = "PC Tasks GET Operation"
  method              = "GET"
  url_template        = "/tasks/*"
  description         = "Calls PC Tasks GET Operation"
}

resource "azurerm_api_management_api_operation" "tasks_post_op" {
  operation_id        = "pctaskspostop"
  api_name            = azurerm_api_management_api.pctasks.name
  api_management_name = azurerm_api_management.pctasks.name
  resource_group_name = azurerm_resource_group.pctasks.name
  display_name        = "PC Tasks GET Operation"
  method              = "POST"
  url_template        = "/tasks/*"
  description         = "Calls PC Tasks POST Operation"
}

resource "azurerm_api_management_api_operation" "tasks_options_op" {
  operation_id        = "pctasksoptionsop"
  api_name            = azurerm_api_management_api.pctasks.name
  api_management_name = azurerm_api_management.pctasks.name
  resource_group_name = azurerm_resource_group.pctasks.name
  display_name        = "PC Tasks OPTIONS Operation"
  method              = "OPTIONS"
  url_template        = "/tasks/*"
  description         = "Calls PC Tasks OPTIONS Operation"
}

resource "azurerm_api_management_api_policy" "pctasks_policy" {
  api_name            = azurerm_api_management_api.pctasks.name
  api_management_name = azurerm_api_management.pctasks.name
  resource_group_name = azurerm_resource_group.pctasks.name

  depends_on = [
    azurerm_api_management_named_value.pctasks_access_key
  ]

  xml_content = <<XML
    <policies>
    <inbound>
        <base />
        <set-backend-service backend-id="pctasks-backend" />
        <set-header name="host" exists-action="override">
            <value>@(context.Request.OriginalUrl.ToUri().Host)</value>
        </set-header>
        <set-header name="X-Has-Subscription" exists-action="override">
             <value>@{
             if (context.Subscription != null && !String.IsNullOrEmpty(
                 context.Subscription.Key
             ))
             {
                 return "true";
             }
             return "false"; }</value>
        </set-header>
        <set-header name="X-Subscription-Key" exists-action="override">
             <value>@{
             if (context.Subscription != null)
             {
                 return context.Subscription.Key;
             }
             return null; }</value>
        </set-header>
        <set-header name="X-User-Email" exists-action="override">
             <value>@{
             if (context.User != null)
             {
                 return context.User.Email;
             }
             return null; }</value>
        </set-header>
        <set-header name="X-Access-Key" exists-action="override">
             <value>{{pctasks-apim-access-key}}</value>
        </set-header>
        <rate-limit-by-key calls="100" renewal-period="1" counter-key="@(context.Request.IpAddress)" />
    </inbound>
    <outbound>
        <base />
    </outbound>
</policies>

  XML
}
