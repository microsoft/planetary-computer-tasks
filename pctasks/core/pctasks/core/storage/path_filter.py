import os
import re
from typing import List, Optional, Set

from pctasks.core.utils import map_opt


class PathFilter:
    """Filter paths by name, extension, or regex.

    Args:
        name_starts_with: Optional prefix that path must have to pass filter.
        extensions: Optional list of extensions that path must have to pass filter.
        ends_with: Optional string that path must end with to pass filter.
        matches: Optional regex that path must match to pass filter.
    """

    def __init__(
        self,
        name_starts_with: Optional[str] = None,
        extensions: Optional[List[str]] = None,
        ends_with: Optional[str] = None,
        matches: Optional[str] = None,
    ):
        def _transform_extensions(ext: List[str]) -> Set[str]:
            result: Set[str] = set()
            for e in ext:
                if not e.startswith("."):
                    e = f".{e}"
                result.add(e.lower())
            return result

        self.name_starts_with = name_starts_with
        self.extensions = map_opt(_transform_extensions, extensions)
        self.ends_with = ends_with
        self.matches = map_opt(lambda x: re.compile(x), matches)

    def __call__(self, path: str) -> bool:
        if self.name_starts_with and not path.startswith(self.name_starts_with):
            return False
        if self.extensions:
            ext = os.path.splitext(path)[1].lower()
            if ext not in self.extensions:
                return False
        if self.ends_with and not path.endswith(self.ends_with):
            return False
        if self.matches and self.matches.search(path) is None:
            return False
        return True
