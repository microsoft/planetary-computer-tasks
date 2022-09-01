import logging
from typing import Optional

from fastapi import Request

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


class ParsedRequest:
    def __init__(self, request: Request) -> None:
        settings = ServerSettings.get()
        self._request = request
        self.dev = settings.dev
        self.dev_api_key = settings.dev_api_key
        self.dev_auth_token = settings.dev_auth_token
        self.access_key = settings.access_key

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
