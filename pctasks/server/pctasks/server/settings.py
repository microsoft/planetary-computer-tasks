from pctasks.core.settings import PCTasksSettings


class ServerSettings(PCTasksSettings):
    @classmethod
    def section_name(cls) -> str:
        return "server"

    runner_image: str
    server_account_key: str
