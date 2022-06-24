from typing import Dict

from pydantic import Field

from pctasks.core.models.config import ImageConfig
from pctasks.core.settings import PCTasksSettings


class SubmitSettings(PCTasksSettings):
    @classmethod
    def section_name(cls) -> str:
        return "submit"

    endpoint: str
    api_key: str
    image_keys: Dict[str, ImageConfig] = Field(default_factory=dict)
