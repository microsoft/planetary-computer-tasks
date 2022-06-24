from typing import Dict, List, Optional

from pydantic import validator

from pctasks.core.models.base import PCBaseModel


class QueueSasConfig(PCBaseModel):
    account_url: str
    queue_name: str
    sas_token: str

    def __str__(self) -> str:
        return f"{self.account_url}/{self.queue_name}"


class QueueConnStrConfig(PCBaseModel):
    connection_string: str
    queue_name: str

    def __str__(self) -> str:
        return f"CONNECTIONSTRING/{self.queue_name}"


class TableSasConfig(PCBaseModel):
    account_url: str
    table_name: str
    sas_token: str


class TableAccountKeyConfig(PCBaseModel):
    account_url: str
    account_name: str
    account_key: str
    table_name: str


class BlobConfig(PCBaseModel):
    account_url: Optional[str]
    uri: str
    sas_token: str


class ImageConfig(PCBaseModel):
    image: str
    environment: Optional[List[str]] = None
    tags: Optional[List[str]] = None

    @validator("environment")
    def _environment_validator(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v:
            for env in v:
                if not len(env.split("=")) == 2:
                    raise ValueError(f"Environment entry {env} is invalid.")
        return v

    @validator("tags")
    def _tags_validator(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v:
            for tag in v:
                if not len(tag.split("=")) == 2:
                    raise ValueError(f"Tags entry {tag} is invalid.")
        return v

    def get_environment(self) -> Optional[Dict[str, str]]:
        if not self.environment:
            return None
        return {k: v.strip() for k, v in [e.split("=") for e in self.environment]}

    def merge_env(self, env: Optional[Dict[str, str]]) -> Optional[Dict[str, str]]:
        if self.environment:
            new_env = env or {}
            for line in self.environment:
                k, v = [x.strip() for x in line.split("=")]
                if k not in new_env:
                    new_env[k] = v
            return new_env
        else:
            return env

    def get_tags(self) -> Optional[Dict[str, str]]:
        if not self.tags:
            return None
        return {k: v.strip() for k, v in [e.split("=") for e in self.tags]}


class CodeConfig(PCBaseModel):
    src: Optional[str]
    requirements: Optional[str]
    pip_options: Optional[List[str]]
