from typing import Optional

from pydantic import model_validator
from typing_extensions import Self

from pctasks.core.settings import PCTasksSettings


class ServerSettings(PCTasksSettings):
    @classmethod
    def section_name(cls) -> str:
        return "server"

    request_timeout: int = 30

    dev: bool = False
    dev_api_key: Optional[str] = None
    dev_auth_token: Optional[str] = None

    access_key: Optional[str] = None

    app_insights_instrumentation_key: Optional[str] = None

    @model_validator(mode="after")
    def _dev_api_key_validator(self) -> Self:
        if self.dev:
            if not self.dev_api_key:
                raise ValueError("dev_api_key is required when dev is True")
        return self

    @model_validator(mode="after")
    def _dev_auth_token_validator(self) -> Self:
        if self.dev:
            if not self.dev_auth_token:
                raise ValueError("dev_auth_token is required when dev is True")
        return self
