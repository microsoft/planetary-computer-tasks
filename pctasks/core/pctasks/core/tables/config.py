from typing import List, Optional

from pctasks.core.constants import DEFAULT_TARGET_ENVIRONMENT
from pctasks.core.models.config import ImageConfig
from pctasks.core.tables.base import StrTableService
from pctasks.core.utils import map_opt


class ImageKeyEntryTable(StrTableService):
    _columns = ["image", "environment"]

    def _parse_env(self, env: str) -> List[str]:
        return env.split("||")

    def _encode_env(self, env: List[str]) -> str:
        return " || ".join(env)

    def get_image(
        self, key: str, target_environment: Optional[str]
    ) -> Optional[ImageConfig]:

        row_key = target_environment or DEFAULT_TARGET_ENVIRONMENT

        result = self.get(partition_key=key, row_key=row_key)
        if not result:
            return None
        image = result.get("image")
        if not image:
            return None
        env = result.get("environment")
        return ImageConfig(
            image=image,
            environment=map_opt(self._parse_env, env),
        )

    def set_image(
        self,
        image_key: str,
        image_config: ImageConfig,
        target_environment: Optional[str] = None,
    ) -> None:
        row_key = target_environment or DEFAULT_TARGET_ENVIRONMENT
        values = image_config.dict()
        if "environment" in values:
            values["environment"] = self._encode_env(values["environment"])
        self.upsert(partition_key=image_key, row_key=row_key, values=values)
