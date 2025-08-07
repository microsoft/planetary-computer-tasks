from azure.identity import DefaultAzureCredential
import os


def get_credential() -> DefaultAzureCredential:
    return (
        DefaultAzureCredential()  # CodeQL [SM05139] In Production environments, managed identity is already set up.
        # so we can use DefaultAzureCredential directly
    )
