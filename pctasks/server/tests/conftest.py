import pytest
from starlette.testclient import TestClient

from pctasks.server.main import app


@pytest.fixture(scope="function")
def client() -> TestClient:
    return TestClient(app)
