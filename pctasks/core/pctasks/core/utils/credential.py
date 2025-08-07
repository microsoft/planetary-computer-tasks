
from azure.identity import ManagedIdentityCredential, DefaultAzureCredential
import os

def get_credential(
    use_managed_identity: bool | None = None, use_azure_cli: bool | None = None
) ->  DefaultAzureCredential:
    """
    Get the appropriate Azure credential based on environment variables or defaults.
    """
    if use_managed_identity is None:
        use_managed_identity = os.environ.get("AZURE_CLIENT_ID") is not None

    if use_managed_identity:
        return ManagedIdentityCredential()
    else:
        return DefaultAzureCredential() # CodeQL [SM05139] In Production Managed Identity is set and this is not used in production, so this is safe.
