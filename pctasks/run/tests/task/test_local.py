from types import SimpleNamespace
from typing import Dict

import pytest

from pctasks.run.task.local import LocalTaskRunner

TOKEN = "test-local-token"
EXPECTED_HEADERS = {"Authorization": f"Bearer {TOKEN}"}


class FakeResponse:
    status_code = 200
    text = ""

    def __init__(self, payload: Dict[str, str]) -> None:
        self.payload = payload

    def json(self) -> Dict[str, str]:
        return self.payload


def test_submit_sends_authentication_header(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_headers: Dict[str, str] = {}

    def post(url: str, data: bytes, headers: Dict[str, str]) -> FakeResponse:
        captured_headers.update(headers)
        return FakeResponse({"id": "task-id"})

    monkeypatch.setattr("pctasks.run.task.local.requests.post", post)
    prepared_task = SimpleNamespace(
        task_input_blob_config=SimpleNamespace(
            uri="blob://account/container/input.json",
            sas_token="token",
            account_url=None,
        ),
        task_data=SimpleNamespace(tags={}),
    )

    runner = LocalTaskRunner("http://local-dev-endpoints:8512", TOKEN)
    results = runner.submit_tasks([prepared_task])  # type: ignore[list-item]

    assert results[0].success
    assert captured_headers == EXPECTED_HEADERS


def test_poll_sends_authentication_header(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_headers: Dict[str, str] = {}

    def get(url: str, headers: Dict[str, str]) -> FakeResponse:
        captured_headers.update(headers)
        return FakeResponse({"task_status": "completed"})

    monkeypatch.setattr("pctasks.run.task.local.requests.get", get)

    runner = LocalTaskRunner("http://local-dev-endpoints:8512", TOKEN)
    result = runner.poll_task({"id": "task-id"}, previous_poll_count=0)

    assert result.task_status.value == "completed"
    assert captured_headers == EXPECTED_HEADERS
