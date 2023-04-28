from typing import Any, Dict, Optional

from pydantic import validator

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

    @validator("dev_api_key", always=True)
    def _dev_api_key_validator(
        cls, v: Optional[str], values: Dict[str, Any]
    ) -> Optional[str]:
        if values.get("dev"):
            if not v:
                raise ValueError("dev_api_key is required when dev is True")
        return v

    @validator("dev_auth_token", always=True)
    def _dev_auth_token_validator(
        cls, v: Optional[str], values: Dict[str, Any]
    ) -> Optional[str]:
        if values.get("dev"):
            if not v:
                raise ValueError("dev_auth_token is required when dev is True")
        return v
