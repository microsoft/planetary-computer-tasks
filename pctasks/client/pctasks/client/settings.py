from typing import Dict, Optional
from urllib.parse import urlparse

from pydantic import validator

from pctasks.core.models.workflow import WorkflowSubmitMessage
from pctasks.core.settings import PCTasksSettings


class ClientSettings(PCTasksSettings):
    @classmethod
    def section_name(cls) -> str:
        return "client"

    endpoint: str
    api_key: str
    confirmation_required: bool = True
    default_args: Optional[Dict[str, str]] = None

    @validator("endpoint")
    def _validate_endpoint(cls, v: str) -> str:
        try:
            parsed = urlparse(v)
            if parsed.scheme not in ["http", "https"]:
                raise Exception()
        except Exception:
            raise ValueError(f"{v} is not a valid URL")
        return v

    def add_default_arguments(self, submit_message: WorkflowSubmitMessage) -> None:
        """Modifies the submit message to include default arguments."""
        if self.default_args:
            for arg_name, arg_value in self.default_args.items():
                if (
                    submit_message.workflow.args
                    and arg_name in submit_message.workflow.args
                ):
                    if not submit_message.args:
                        submit_message.args = {}
                    if arg_name not in submit_message.args:
                        submit_message.args[arg_name] = arg_value
