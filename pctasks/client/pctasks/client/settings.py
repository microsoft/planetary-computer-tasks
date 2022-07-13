from typing import Dict

from pydantic import Field

from pctasks.core.models.config import ImageConfig
from pctasks.core.settings import PCTasksSettings


class ClientSettings(PCTasksSettings):
    @classmethod
    def section_name(cls) -> str:
        return "client"

    endpoint: str
    api_key: str
    # TODO: Remove
    image_keys: Dict[str, ImageConfig] = Field(default_factory=dict)
