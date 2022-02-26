from typing import Dict

from pctasks.execute.secrets.base import SecretsProvider


class MockSecretsProvider(SecretsProvider):
    def __init__(self, secrets: Dict[str, str]) -> None:
        self.secrets = secrets

    def get_secret(self, name: str) -> str:
        result = self.secrets.get(name, None)
        if not result:
            raise ValueError(f"Secret {name} requested but not provided")
        return result


def test_parse_secret():
    provider = MockSecretsProvider({"foo": "bar"})
    env = {"foo": "${{ secrets.foo }}"}
    parsed = provider.substitute_secrets(env)
    assert parsed["foo"] == "bar"
