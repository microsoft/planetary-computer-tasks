import importlib.metadata
import os
import time
import warnings
from importlib.metadata import EntryPoint
from typing import List, Type, TypeVar

T = TypeVar("T")


def get_plugin_subcommands(command_type: Type[T], entry_point_group: str) -> List[T]:
    result: List[T] = []
    entry_points: List[EntryPoint] = list(
        importlib.metadata.entry_points(group=entry_point_group)
    )

    start = time.perf_counter()
    PCTASKS_DEBUG = os.environ.get("PCTASKS_DEBUG", "")

    for entry_point in entry_points:
        try:
            t0 = time.time()
            subcommand = entry_point.load()
            t1 = time.time()
            if PCTASKS_DEBUG:
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

    if PCTASKS_DEBUG:
        end = time.perf_counter()
        print(f"Finished in {end - start:0.2f}s")

    return result
