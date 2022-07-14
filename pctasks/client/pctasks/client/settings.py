from pctasks.core.settings import PCTasksSettings


class ClientSettings(PCTasksSettings):
    @classmethod
    def section_name(cls) -> str:
        return "client"

    endpoint: str
    api_key: str
