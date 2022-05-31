import os
from typing import Any, Dict, Optional

from pctasks.run.secrets.local import LOCAL_SECRETS_PREFIX


class TempSecrets:
    """Creates temporary secrets for testing.

    Does this by setting the proper environment variables
    in a context manager, clearing them out on exit.
    """

    def __init__(self, secrets: Dict[str, str]):
        self._secrets: Dict[str, Optional[str]] = {k: v for k, v in secrets.items()}

    def __enter__(self) -> "TempSecrets":
        for name in self._secrets:
            env_name = f"{LOCAL_SECRETS_PREFIX}{name}"
            prev_value = os.getenv(env_name)
            os.environ[env_name] = str(self._secrets[name])
            self._secrets[name] = prev_value

        return self

    def __exit__(self, *args: Any) -> None:
        for name in self._secrets:
            env_name = f"{LOCAL_SECRETS_PREFIX}{name}"
            if self._secrets[name] is None:
                del os.environ[env_name]
            else:
                os.environ[env_name] = str(self._secrets[name])
