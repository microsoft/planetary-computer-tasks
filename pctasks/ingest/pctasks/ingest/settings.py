from typing import Dict, Optional

from pydantic import Field

from pctasks.core.models.base import PCBaseModel
from pctasks.core.settings import PCTasksSettings
from pctasks.ingest.constants import DEFAULT_INSERT_GROUP_SIZE

SECTION_NAME = "ingest"
DEFAULT_IMAGE_KEY = "ingest"


class IngestConfig(PCBaseModel):
    insert_group_size: int = DEFAULT_INSERT_GROUP_SIZE
    """Number of items to insert into the database per bulk load."""
    insert_only: bool = False
    """If your sure you're only doing inserts, use this flag for performance gains."""
    num_workers: Optional[int] = None
    """The number of workers to use for ingest. Defaults to the number of cores."""
    work_mem: Optional[int] = None
    """The work_mem setting (in MB) to use for this ingest."""


class ImageKeys(PCBaseModel):
    default: str = Field(default=DEFAULT_IMAGE_KEY)
    targets: Optional[Dict[str, str]] = None

    def get_key(self, target: Optional[str] = None) -> str:
        if target and self.targets:
            return self.targets.get(target, self.default)
        return self.default


class IngestSettings(PCTasksSettings):
    @classmethod
    def section_name(cls) -> str:
        return SECTION_NAME

    config: IngestConfig = Field(default_factory=IngestConfig)
    image_keys: ImageKeys = Field(default_factory=ImageKeys)
