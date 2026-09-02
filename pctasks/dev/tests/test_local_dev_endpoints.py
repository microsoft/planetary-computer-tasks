from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from pctasks.dev.local_dev_endpoints import (
    FAIL_SUBMIT_TAG,
    LOCAL_DEV_ENDPOINTS_TOKEN_ENV_VAR,
    app,
)

TOKEN = "test-local-token"
AUTH_HEADERS = {"Authorization": f"Bearer {TOKEN}"}


def test_endpoints_fail_closed_without_configured_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(LOCAL_DEV_ENDPOINTS_TOKEN_ENV_VAR, raising=False)

    with TestClient(app) as client:
        assert client.post("/execute", json={"args": []}).status_code == 503
        assert client.get("/poll/missing").status_code == 503
        assert client.get("/secrets/test").status_code == 503


def test_endpoints_reject_missing_or_invalid_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(LOCAL_DEV_ENDPOINTS_TOKEN_ENV_VAR, TOKEN)

    with TestClient(app) as client:
        assert client.post("/execute", json={"args": []}).status_code == 401
        assert client.get("/poll/missing").status_code == 401
        assert client.get("/secrets/test").status_code == 401
        assert (
            client.get(
                "/secrets/test", headers={"Authorization": "Bearer invalid"}
            ).status_code
            == 401
        )


def test_authenticated_execute_and_poll(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(LOCAL_DEV_ENDPOINTS_TOKEN_ENV_VAR, TOKEN)

    with TestClient(app) as client:
        response = client.post(
            "/execute",
            headers=AUTH_HEADERS,
            json={"args": [], "tags": {FAIL_SUBMIT_TAG: "true"}},
        )
        assert response.status_code == 200
        task_id = response.json()["id"]

        poll_response = client.get(f"/poll/{task_id}", headers=AUTH_HEADERS)
        assert poll_response.status_code == 200


def test_authenticated_secret_access(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv(LOCAL_DEV_ENDPOINTS_TOKEN_ENV_VAR, TOKEN)
    secrets_file = tmp_path / "secrets.yaml"
    secrets_file.write_text("test: secret-value\n")
    monkeypatch.setenv("DEV_SECRETS_FILE", str(secrets_file))

    with TestClient(app) as client:
        response = client.get("/secrets/test", headers=AUTH_HEADERS)

    assert response.status_code == 200
    assert response.text == "secret-value"
