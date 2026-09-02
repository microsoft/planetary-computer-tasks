from types import SimpleNamespace
from typing import Dict, cast

import pytest

from pctasks.run.secrets.local import LocalSecretsProvider
from pctasks.run.settings import RunSettings

TOKEN = "test-local-token"


class FakeResponse:
    status_code = 200
    text = "secret-value"


def test_secret_request_sends_authentication_header(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_headers: Dict[str, str] = {}

    def get(url: str, headers: Dict[str, str]) -> FakeResponse:
        captured_headers.update(headers)
        return FakeResponse()

    monkeypatch.setattr("pctasks.run.secrets.local.requests.get", get)
    settings = cast(
        RunSettings,
        SimpleNamespace(
            local_dev_endpoints_url="http://local-dev-endpoints:8512",
            local_dev_endpoints_token=TOKEN,
        ),
    )
    provider = LocalSecretsProvider(settings)

    assert provider.get_secret("test") == "secret-value"
    assert captured_headers == {"Authorization": f"Bearer {TOKEN}"}
