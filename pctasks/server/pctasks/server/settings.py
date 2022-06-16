from pydantic import BaseModel

from pctasks.core.settings import PCTasksSettings


class ArgoSettings(BaseModel):
    host: str
    token: str
    namespace: str = "argo"


class ServerSettings(PCTasksSettings):
    @classmethod
    def section_name(cls) -> str:
        return "server"

    argo: ArgoSettings

    runner_image: str
    server_account_key: str
