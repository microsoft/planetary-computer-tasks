from typing import Optional

from fastapi import Request

from pctasks.server.settings import ServerSettings

# Headers containing user data from API Management
HAS_SUBSCRIPTION_HEADER = "X-Has-Subscription"
SUBSCRIPTION_KEY_HEADER = "X-Subscription-Key"
USER_EMAIL_HEADER = "X-User-Email"

API_KEY_HEADER = "PC-API-KEY"


class ParsedRequest:
    def __init__(self, request: Request) -> None:
        settings = ServerSettings.get()
        self._request = request
        self.dev = settings.dev
        self.dev_api_key = settings.dev_api_key

    @property
    def is_authenticated(self) -> bool:
        if self.dev:
            return self._request.headers.get(API_KEY_HEADER) == self.dev_api_key
        return (
            self.has_subscription
            and bool(self.subscription_key)
            and bool(self.user_email)
        )

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
            if self._request.headers.get(API_KEY_HEADER) == self.dev_api_key:
                return "dev@null.com"
            else:
                return None

        result = self._request.headers.get(USER_EMAIL_HEADER)
        if not result:
            return None
        return result
