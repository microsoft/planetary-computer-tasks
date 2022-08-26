# Azure AD App Registrations

This PC Tasks API and frontend use Azure AD App Registrations to authenticate
users and provide authorization scopes. These applications cannot be
automatically created via the existing terraform deployment code, and instead
must be created manually using the Application Manifest templates located in the
`deployment/manual` directory. Read more about the [Manifest file
schema](https://docs.microsoft.com/en-us/azure/active-directory/develop/reference-app-manifest),
and [using Azure AD to protect API
resources](https://docs.microsoft.com/en-us/azure/active-directory/develop/scenario-protected-web-api-overview).

## Overview

1. Create a new Azure AD App Registration for the PC Tasks API backend app ("the backend app")
2. Create a new Azure AD App Registration for the PC Tasks API frontend app ("the frontend app")
3. Extract values from the initial registrations and merge them into the corresponding app registration manifest template files.
4. In the Azure portal, update the app registrations with the new manifest data.
5. Update the deployment secrets with the new app registration ids.

### Create new app registrations

Go to the [Azure portal](https://portal.azure.com) and create a new app registration for the backend app:

- Give it a description name that includes the environment it targets, e.g., `pctasks-production-backend-app`.
- Keep the remaining defaults, these values will be set by updating the application manifest later.
- Make a note of the Application ID value for later.

Create a second app registration for the frontend app:

- Give it a description name that includes the environment it targets, e.g., `pctasks-production-frontend-app`.
- Make a note of the Application ID value for later.

### Merge app registration values into manifest files templates

You'll need to take 4 values from newly created app registrations and merge them into the corresponding app registration manifest template files. Do this for **both** the backend and frontend manifest templates.

| Manifest key name | Template marker               |
|-------------------|-------------------------------|
| `id`              | `{{ application_system_id }}` |
| `appId`           | `{{ application_id }}`        |
| `name`            | `{{ application_name }}`      |
| `createdDateTime` | `{{ created_date_time }}`     |

#### Update backend app manifest values

Updating the manifest file itself is a two-step process because it contains
self-referencing values. First, update the backend app manifest file to include
new values:

| Manifest key name                    | Template marker                     | Value                                                                                                       |
|--------------------------------------|-------------------------------------|-------------------------------------------------------------------------------------------------------------|
| `identifierUris`                     | `{{ application_identifier_uris }}` | List of single value, `api://{{ backend_application_name }}/`, e.g. `api://pctaskstest-staging-backend-app` |
| `preAuthorizedApplications[0].appId` | `{{ frontend_app_id }}`             | The Application ID of the frontend app created earlier                                                      |

Then, go to the Azure portal and update the backend app registration with the new manifest values:

- Click the "Manifest" link under the "Manage" heading
- Replace the existing manifest file with the fully templated new manifest file
- **Temporarily remove the value for `preAuthorizedApplications`**. Cut the value of the list so it's just an empty array (`[]`). We can't reference the permission ids that are also being created from the manifest file.
- Click save
- Paste back the preAuthorizedApplications value
- Click save

#### Update frontend app manifest values

First, update the frontend app manifest file to include new values:

| Manifest key name                         | Template marker             | Value                                                                                                          |
|-------------------------------------------|-----------------------------|----------------------------------------------------------------------------------------------------------------|
| `replyUrlsWithType[1].url`                | `website_auth_callback_url` | The URL of the website this app registration represents, or a placeholder value if the app is not deployed yet |
| `requiredResourceAccess[1].resourceAppId` | `{{ backend_app_id }}`      | The Application ID of the backend app created earlier                                                          |

Then, go to the Azure portal and update the frontend app registration with the new manifest values:

- Click the "Manifest" link under the "Manage" heading
- Replace the existing manifest file with the fully templated new manifest file
- Click save

The applications are now configured. If structural changes are made to either in the portal, be sure to sync those changes with the template files in this repository.

### Update deployment secrets

Update the deployment secrets with the new app registration ids:

- `backend_api_app_id_secret_name`: Update the deploy secret referenced by this tf variable to the new backend app registration id. This will allow the APIM policy to access it as a named value and verify that the correct audience claim is present in generated access tokens.
