import logging
from typing import Dict, Optional, Union
from urllib.parse import urlparse

from fastapi import Request

from pctasks.server.constants import (
    DIMENSION_KEYS,
    HEADER_REQUEST_ID,
    HTTP_METHOD,
    HTTP_PATH,
    HTTP_URL,
    QS_REQUEST_ENTITY,
    SERVICE_NAME,
    X_AZURE_REF,
    X_REQUEST_ENTITY,
)
from pctasks.server.settings import ServerSettings

# Headers containing user data from API Management
HAS_AUTHORIZATION_HEADER = "X-Has-Authorization"
AUTHORIZATION_HEADER = "Authorization"
HAS_SUBSCRIPTION_HEADER = "X-Has-Subscription"
SUBSCRIPTION_KEY_HEADER = "X-Subscription-Key"
USER_EMAIL_HEADER = "X-User-Email"
ACCESS_KEY_HEADER = "X-Access-Key"

API_KEY_HEADER = "X-API-KEY"


logger = logging.getLogger(__name__)


def get_request_entity(request: Request) -> Union[str, None]:
    """Get the request entity from the given request. If not present as a
    header, attempt to parse from the query string
    """
    return request.headers.get(X_REQUEST_ENTITY) or request.query_params.get(
        QS_REQUEST_ENTITY
    )


class ParsedRequest:
    def __init__(self, request: Request) -> None:
        settings = ServerSettings.get()
        self._request = request
        self.dev = settings.dev
        self.dev_api_key = settings.dev_api_key
        self.dev_auth_token = settings.dev_auth_token
        self.access_key = settings.access_key

    @property
    def path(self) -> str:
        parsed_url = urlparse(f"{self._request.url}")
        return parsed_url.path

    @property
    def is_authenticated(self) -> bool:
        """Authenticated users can pass in a valid subscription key or access
        token (JWT). In either case the request must include the secret access
        key set by the API gateway."""
        if self.dev:
            return self.has_subscription or self.has_authorization

        if self.access_key:
            if not self.request_access_key == self.access_key:
                logger.warning("Request made with mismatched access key")
                return False
        else:
            logger.warning("Access key is unset in non-dev environment!")

        has_subscription_key = (
            self.has_subscription
            and bool(self.subscription_key)
            and bool(self.user_email)
        )

        has_access_token = self.has_authorization and bool(self.user_email)

        return has_subscription_key or has_access_token

    @property
    def has_authorization(self) -> bool:
        """Determines whether or not this request has a validated access token (JWT)."""
        if self.dev:
            return (
                self._request.headers.get(AUTHORIZATION_HEADER) == self.dev_auth_token
            )

        return self._request.headers.get(HAS_AUTHORIZATION_HEADER) == "true"

    @property
    def has_subscription(self) -> bool:
        """Determines whether or not this request has an authorized subscription"""
        if self.dev:
            return self._request.headers.get(API_KEY_HEADER) == self.dev_api_key

        return self._request.headers.get(HAS_SUBSCRIPTION_HEADER) == "true"

    @property
    def subscription_key(self) -> Optional[str]:
        """Retrieves the subscription key from headers

        API Management will set the header to an empty string if there is no
        subscription key. This function translates that to None.
        """
        if self.dev:
            return self.dev_api_key

        result = self._request.headers.get(SUBSCRIPTION_KEY_HEADER)
        if not result:
            return None
        return result

    @property
    def user_email(self) -> Optional[str]:
        """Retrieves the user email from headers

        API Management will set the header to an empty string if there is no
        user email. This function translates that to None.
        """
        if self.dev:
            if self.has_authorization or self.has_subscription:
                return "dev@null.com"
            else:
                return None

        result = self._request.headers.get(USER_EMAIL_HEADER)
        if not result:
            return None
        return result

    @property
    def request_access_key(self) -> Optional[str]:
        """Retrieves the access key from headers

        API Management can be configured to inject an access key that must match
        the settings of the server in order to be considered legitimate.
        """
        result = self._request.headers.get(ACCESS_KEY_HEADER)
        if not result:
            return None
        return result

    @property
    def custom_dimensions(self) -> Dict[str, Optional[str]]:
        """Retrieves some common information from the request to log to App Insights"""

        # 'request_id' header that can tie a traces entry to a request entry
        # in App Insights. This is set by the API Management gateway.
        # The header is in the format 'request_id: 1234.5678' where the first
        # part is the request id that is logged in the traces entry.
        request_id = _remove_after_dot(self._request.headers.get(HEADER_REQUEST_ID))

        dimensions: Dict[str, Optional[str]] = {
            "ref_id": self._request.headers.get(X_AZURE_REF),
            "request_entity": get_request_entity(self._request),
            "service": SERVICE_NAME,
            HTTP_URL: str(self._request.url),
            HTTP_METHOD: str(self._request.method),
            HTTP_PATH: self.path,
            DIMENSION_KEYS.REQUEST_ID: request_id,
            DIMENSION_KEYS.SUBSCRIPTION_KEY: self.subscription_key,
            DIMENSION_KEYS.USER_EMAIL: self.user_email,
            DIMENSION_KEYS.REQUEST_URL: str(self._request.url),
        }

        return dimensions


def _remove_after_dot(s: Optional[str]) -> Optional[str]:
    if not s:
        return None
    parts = s.split(".")
    if len(parts) == 1:
        return s
    return parts[0] + "."
