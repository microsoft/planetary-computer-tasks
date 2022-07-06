import os
import time
import importlib.metadata
import warnings
from dataclasses import dataclass
from importlib.metadata import EntryPoint
from typing import List, Optional, Type, TypeVar

T = TypeVar("T")


@dataclass
class PCTasksCommandContext:
    """Context used in the pctasks CLI."""

    profile: Optional[str] = None
    """Settings profile. Determines which settings file is read."""

    settings_file: Optional[str] = None
    """Full path to the settings file. If present, overrides the profile."""


def get_plugin_subcommands(command_type: Type[T], entry_point_group: str) -> List[T]:
    result: List[T] = []
    entry_points: List[EntryPoint] = list(
        importlib.metadata.entry_points().get(entry_point_group) or []
    )
    for entry_point in entry_points:
        try:
            t0 = time.time()
            subcommand = entry_point.load()
            t1 = time.time()
            if os.environ.get("PCTASKS_DEBUG", None):
                print(f"loaded {entry_point} in {t1 - t0:0.2f}s")

        except Exception as e:
            warnings.warn(
                f"Failed to load '{entry_point.group}' "
                f"plugin at '{entry_point.name} = {entry_point.value}': {e}"
            )
            continue
        if not isinstance(subcommand, command_type):
            warnings.warn(
                f"{entry_point.value} is registered as an {entry_point.group} "
                f"entry point but is not an instance of {command_type}."
            )
        else:
            result.append(subcommand)

    return result
