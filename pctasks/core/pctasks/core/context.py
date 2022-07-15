from dataclasses import dataclass
from typing import Optional


@dataclass
class PCTasksCommandContext:
    """Context used in the pctasks CLI."""

    profile: Optional[str] = None
    """Settings profile. Determines which settings file is read."""

    settings_file: Optional[str] = None
    """Full path to the settings file. If present, overrides the profile."""
