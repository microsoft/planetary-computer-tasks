from typing import List, Optional

from pctasks.core.models.base import TargetEnvironment
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
        self, key: str, target_environment: TargetEnvironment
    ) -> Optional[ImageConfig]:
        result = self.get(partition_key=key, row_key=str(target_environment))
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
        target_environment: TargetEnvironment,
    ) -> None:
        values = image_config.dict()
        if "environment" in values:
            values["environment"] = self._encode_env(values["environment"])
        self.upsert(
            partition_key=image_key, row_key=str(target_environment), values=values
        )
