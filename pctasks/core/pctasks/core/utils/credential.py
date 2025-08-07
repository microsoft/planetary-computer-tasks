
from azure.identity import ManagedIdentityCredential, AzureCliCredential, DefaultAzureCredential
import os

def get_credential(
    use_managed_identity: bool | None = None, use_azure_cli: bool | None = None
) ->  ManagedIdentityCredential | AzureCliCredential | DefaultAzureCredential:
    """
    Get the appropriate Azure credential based on environment variables or defaults.
    """
    if use_managed_identity is None:
        use_managed_identity = os.environ.get("PCONBOARDING_USE_MANAGED_IDENTITY")

    if use_azure_cli is None:
        use_azure_cli = os.environ.get("PCONBOARDING_USE_AZURE_CLI")

    if use_managed_identity:
        return ManagedIdentityCredential()
    elif use_azure_cli:
        return AzureCliCredential()
    else:
        return DefaultAzureCredential() # CodeQL [SM05139] In Production Managed Identity is set and this is not used in production, so this is safe.
