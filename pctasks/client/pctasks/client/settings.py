from typing import Dict, Optional
from urllib.parse import urlparse

from pydantic import field_validator

from pctasks.core.models.workflow import WorkflowDefinition
from pctasks.core.settings import PCTasksSettings

DEFAULT_PAGE_SIZE = 100


class ClientSettings(PCTasksSettings):
    @classmethod
    def section_name(cls) -> str:
        return "client"

    endpoint: str
    api_key: str
    access_key: Optional[str] = None
    confirmation_required: bool = True
    default_args: Optional[Dict[str, str]] = None
    default_page_size: int = DEFAULT_PAGE_SIZE

    @field_validator("endpoint", mode="after")
    def _validate_endpoint(cls, v: str) -> str:
        try:
            parsed = urlparse(v)
            if parsed.scheme not in ["http", "https"]:
                raise Exception()
        except Exception:
            raise ValueError(f"{v} is not a valid URL")
        return v

    def add_default_args(
        self, workflow_definition: WorkflowDefinition, args: Optional[Dict[str, str]]
    ) -> Optional[Dict[str, str]]:
        """Returns a new dictionary with the default args merged in.
        If args is None and there are no default args, returns None.
        """
        result = args.copy() if args else None
        if self.default_args:
            for arg_name, arg_value in self.default_args.items():
                if workflow_definition.args and arg_name in workflow_definition.args:
                    if not result:
                        result = {}
                    if arg_name not in result:
                        result[arg_name] = arg_value
        return result
