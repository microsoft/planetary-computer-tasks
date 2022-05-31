import os

from pctasks.run.secrets.base import SecretNotFoundError, SecretsProvider

LOCAL_SECRETS_PREFIX = "SECRETS_"


class LocalSecretsProvider(SecretsProvider):
    """SecretsProvider that gets secrets from the environment."""

    def get_secret(self, name: str) -> str:
        env_var = f"{LOCAL_SECRETS_PREFIX}{name}"
        result = os.environ.get(env_var, None)
        if not result:
            raise SecretNotFoundError(
                f"Secret {name} requested but not found: "
                f"no environment variable {env_var}"
            )
        return result
