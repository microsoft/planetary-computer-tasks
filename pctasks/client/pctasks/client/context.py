from dataclasses import dataclass
from typing import Optional

from pctasks.core.context import PCTasksCommandContext


@dataclass
class ClientCommandContext(PCTasksCommandContext):
    pretty_print: bool = False
    """Whether to pretty print the output, e.g. syntax highlight YAML."""

    # PCTasksCommandContext added here to avoid mypy issues

    profile: Optional[str] = None
    """Settings profile. Determines which settings file is read."""

    settings_file: Optional[str] = None
    """Full path to the settings file. If present, overrides the profile."""
