from fastapi.testclient import TestClient

from pctasks.core.utils import ignore_ssl_warnings
from pctasks.server.main import app
from pctasks.server.request import (
    ACCESS_KEY_HEADER,
    HAS_AUTHORIZATION_HEADER,
    HAS_SUBSCRIPTION_HEADER,
    SUBSCRIPTION_KEY_HEADER,
    USER_EMAIL_HEADER,
)
from pctasks.server.settings import ServerSettings

settings = ServerSettings.get()

AUTHORIZED_REQUESTS = [
    # Subscription auth
    {
        HAS_SUBSCRIPTION_HEADER: "true",
        SUBSCRIPTION_KEY_HEADER: "test",
        USER_EMAIL_HEADER: "dev@null.org",
        ACCESS_KEY_HEADER: settings.access_key,
    },
    # Access token auth
    {
        HAS_AUTHORIZATION_HEADER: "true",
        USER_EMAIL_HEADER: "dev@null.org",
        ACCESS_KEY_HEADER: settings.access_key,
    },
    # Access token and subscription auth
    {
        HAS_AUTHORIZATION_HEADER: "true",
        HAS_SUBSCRIPTION_HEADER: "true",
        SUBSCRIPTION_KEY_HEADER: "test",
        USER_EMAIL_HEADER: "dev@null.org",
        ACCESS_KEY_HEADER: settings.access_key,
    },
]

UNAUTHORIZED_REQUESTS = [
    # No auth, with key
    {
        HAS_SUBSCRIPTION_HEADER: "false",
        HAS_AUTHORIZATION_HEADER: "false",
        ACCESS_KEY_HEADER: settings.access_key,
    },
    # Subscription auth, no key
    {
        HAS_SUBSCRIPTION_HEADER: "true",
        SUBSCRIPTION_KEY_HEADER: "test",
        USER_EMAIL_HEADER: "dev@null.org",
    },
    # Access token auth, no key
    {
        HAS_AUTHORIZATION_HEADER: "true",
        USER_EMAIL_HEADER: "dev@null.org",
    },
    # Access token and subscription auth, no key
    {
        HAS_AUTHORIZATION_HEADER: "true",
        HAS_SUBSCRIPTION_HEADER: "true",
        SUBSCRIPTION_KEY_HEADER: "test",
        USER_EMAIL_HEADER: "dev@null.org",
    },
    # No auth headers, with key
    {
        ACCESS_KEY_HEADER: settings.access_key,
    },
    # No headers
    {},
]


def test_authorized_requests():
    for headers in AUTHORIZED_REQUESTS:
        with TestClient(app) as client:
            with ignore_ssl_warnings():
                response = client.get("/workflows", headers=headers)
                assert response.status_code == 200


def test_unauthorized_requests():
    for headers in UNAUTHORIZED_REQUESTS:
        with TestClient(app) as client:
            with ignore_ssl_warnings():
                response = client.get("/workflows", headers=headers)
                assert response.status_code == 401
