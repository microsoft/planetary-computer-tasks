from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from pctasks.core.utils.template import template_dict


class SecretNotFoundError(Exception):
    pass


class SecretsProvider(ABC):
    def substitute_secrets(self, d: Dict[str, Any]) -> Dict[str, Any]:
        """Replaces dictionary with all secrets replaced with their values.

        Secrets are in the form ${{ secret.NAME }}
        """

        def _get_value(path: List[str]) -> Optional[str]:
            if path[0] == "secrets":
                if len(path) == 2:
                    return self.get_secret(path[1])
                else:
                    raise ValueError(f"Invalid secret: {'.'.join(path[1:])}")
            return None

        return template_dict(d, _get_value)

    def __enter__(self) -> "SecretsProvider":
        return self

    def __exit__(self, *args: Any) -> None:
        pass

    @abstractmethod
    def get_secret(self, name: str) -> str:
        pass
