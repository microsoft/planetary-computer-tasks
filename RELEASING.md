# Relesing

Releases are made through the [GitHub UI](https://github.com/microsoft/planetary-computer-tasks/releases/new).
Create a new tag for your release, using the format `<year>.<month>.<count>`.

You also need to update the `pc-test-gha-tags-release` Federated Identity Credential on the `PC Test GitHub Actions Deployment` App Regestration to match the new tag.

```azurecli
az ad app federated-credential update --federated-credential-id "pc-test-gha-tags-release" --id "$CLIENT_ID" --parameters '{"issuer": "https://token.actions.githubusercontent.com", "subject": "repo:microsoft/planetary-computer-tasks:ref:refs/tags/$TAG", "description": "Federated credential for Github Actions to deploy to Azure from microsoft/planetary-computer-tasks with any tag", "audiences": ["api://AzureADTokenExchange"]}'
```

where `$TAG` is something like `2024.6.1`.
