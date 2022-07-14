import os

import requests

from pctasks.run.secrets.base import SecretNotFoundError, SecretsProvider

LOCAL_ENV_SECRETS_PREFIX = "SECRETS_"


class LocalSecretsProvider(SecretsProvider):
    """SecretsProvider that gets secrets from the environment or dev endpoint"""

    def get_secret(self, name: str) -> str:
        env_var = f"{LOCAL_ENV_SECRETS_PREFIX}{name}"
        result = os.environ.get(env_var, None)
        if not result and self.settings:
            # Try dev server
            local_dev_endpoints_url = self.settings.local_dev_endpoints_url
            if local_dev_endpoints_url:
                resp = requests.get(
                    os.path.join(local_dev_endpoints_url, f"secrets/{name}")
                )
                if resp.status_code == 200:
                    result = resp.text

        if not result:
            raise SecretNotFoundError(f"Secret {name} requested but not found: {name}")

        return result
