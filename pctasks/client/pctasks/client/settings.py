from urllib.parse import urlparse

from pydantic import validator

from pctasks.core.settings import PCTasksSettings


class ClientSettings(PCTasksSettings):
    @classmethod
    def section_name(cls) -> str:
        return "client"

    endpoint: str
    api_key: str
    confirmation_required: bool = True

    @validator("endpoint")
    def _validate_endpoint(cls, v: str) -> str:
        try:
            parsed = urlparse(v)
            if parsed.scheme not in ["http", "https"]:
                raise Exception()
        except Exception:
            raise ValueError(f"{v} is not a valid URL")
        return v
