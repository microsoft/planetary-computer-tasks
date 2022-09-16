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

# The tenant id who's openid-connect well-known config is used to verify signing
# of oAuth2 access tokens.
resource "azurerm_api_management_named_value" "pctasks_signing_tenant_id" {
  name                = "pctasks-apim-jwt-signing-tentant-id"
  resource_group_name = azurerm_resource_group.pctasks.name
  api_management_name = azurerm_api_management.pctasks.name
  display_name        = "pctasks-apim-jwt-signing-tentant-id"
  secret              = false
  value               = azurerm_api_management.pctasks.identity[0].tenant_id
}

# The backend app registration App ID which is validated in incoming access
# token `aud` claim.
resource "azurerm_api_management_named_value" "pctasks_backend_app_id" {
  name                = "pctasks-apim-jwt-aud-backend-app-id"
  resource_group_name = azurerm_resource_group.pctasks.name
  api_management_name = azurerm_api_management.pctasks.name
  display_name        = "pctasks-apim-jwt-aud-backend-app-id"
  secret              = true
  value_from_key_vault {
    secret_id = data.azurerm_key_vault_secret.backend_app_id.id
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
    azurerm_api_management_named_value.pctasks_access_key,
    azurerm_api_management_named_value.pctasks_backend_app_id,
    azurerm_api_management_named_value.pctasks_signing_tenant_id
  ]

  xml_content = <<XML
    <policies>
    <inbound>
        <base />
        <set-backend-service backend-id="pctasks-backend" />
        <set-header name="host" exists-action="override">
            <value>@(context.Request.OriginalUrl.ToUri().Host)</value>
        </set-header>
        <!--
            If an optional Authorization header is provided, validate it and set the X-Has-Authorization token. Otherwise,
            ensure the header is overridden to "false". The backend code will need to validate that a subscription key or
            auth token was provided via the headers in this policy.
        -->
        <choose>
            <when condition="@(context.Request.Headers.GetValueOrDefault("Authorization", "") != "")">
                <validate-jwt header-name="Authorization" failed-validation-error-message="Provided authorization token is invalid" require-expiration-time="true" require-scheme="Bearer" require-signed-tokens="true" output-token-variable-name="jwt">
                    <!--JWT must be signed using keys from originating app tenant -->
                    <openid-config url="https://login.microsoftonline.com/{{pctasks-apim-jwt-signing-tentant-id}}/v2.0/.well-known/openid-configuration" />
                    <issuers>
                        <issuer>https://login.microsoftonline.com/{{pctasks-apim-jwt-signing-tentant-id}}/v2.0</issuer>
                    </issuers>
                    <required-claims>
                        <!--JWT must provide correct audience claim from the API backend app registration -->
                        <claim name="aud">
                            <value>{{pctasks-apim-jwt-aud-backend-app-id}}</value>
                        </claim>
                        <!--JWT must provide Run Read and Write API scopes as published by the app registration -->
                        <claim name="scp" separator=" ">
                            <value>Runs.Read.All</value>
                            <value>Runs.Write.All</value>
                        </claim>
                    </required-claims>
                </validate-jwt>
                <set-header name="X-Has-Authorization" exists-action="override">
                    <value>true</value>
                </set-header>
            </when>
            <otherwise>
                <set-header name="X-Has-Authorization" exists-action="override">
                    <value>false</value>
                </set-header>
            </otherwise>
        </choose>
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
             } else if (context.Variables.ContainsKey("jwt"))
             {
                 return ((Jwt)context.Variables["jwt"]).Claims["preferred_username"][0];
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
