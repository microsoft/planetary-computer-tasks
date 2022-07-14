from typing import Optional
from pctasks.core.settings import PCTasksSettings


class TaskSettings(PCTasksSettings):
    @classmethod
    def section_name(cls) -> str:
        return "task"

    code_dir: Optional[str] = None
    """The directory which downloaded code and requirements are stored.

    If provided, this directory will be used as the target for pip installs,
    and code source will be downloaded to this directory.
    If None, will use sys.path and pip install will not use a target directory.
    """
