import json
import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union, cast
from uuid import uuid4

from pydantic import BaseModel

TEMPLATE_REGEX = r"\$\{\{\s*([^\"]*?)\s*\}\}"

LIST_PATH_REGEX = r"(.*)\[(\d+)\]$"

_PAREN_REGEX = r"\((.*?)\)"


T = TypeVar("T", bound=BaseModel)


class TemplateError(Exception):
    pass


TemplateValue = Union[str, List[Any], Dict[str, Any]]
# TemplateValue = Union[str, List["TemplateValue"], Dict[str, Any]]
# If https://github.com/python/mypy/issues/731 is closed, use above.


def find_value(
    data: Dict[str, Any], path: List[str], strict: bool = False
) -> Optional[TemplateValue]:
    """Finds the value of a path in a dictionary.

    If strict is True, raises an exception if there is no key for
    template values. If False, ignores any missing top-level keys.

    Useful in templating methods to utilize a dictionary of parameters.
    Throws a KeyError if the path does not exist.
    Throws a ValueError if the final path is a dict, or if
    there is a non-dict value that is not the final path.

    Handles lists that are represented as suffixes to paths, like
    "parent.child[0].url"
    """

    def _fetch(
        d: Dict[str, Any], path: List[str], fail_if_not_found: bool = False
    ) -> Optional[TemplateValue]:
        head, tail = path[0], path[1:]
        index: Optional[int] = None
        list_m = re.match(LIST_PATH_REGEX, head)
        if list_m:
            head = list_m.group(1)
            index = int(list_m.group(2))
        v = d.get(head)
        if v is None:
            if fail_if_not_found:
                raise TemplateError(
                    f"Element '{head}' not found in template {'.'.join(path)}. "
                    f"Dict: {d}"
                )
            else:
                return None
        else:
            if index:
                if not isinstance(v, list):
                    raise TemplateError(
                        f"Expected list at key {head}, got {type(v)} "
                        f"for template {'.'.join(path)}"
                    )
                else:
                    if (index >= 0 and len(v) <= index) or (
                        index < 0 and len(v) >= -index
                    ):
                        raise TemplateError(
                            f"Index {index} out of range for key {head} "
                            f"for template {'.'.join(path)}"
                        )
                    v = v[index]
            if tail:
                if isinstance(v, dict):
                    return _fetch(v, tail, fail_if_not_found=True)
                elif isinstance(v, list):
                    if len(v) == 0:
                        raise TemplateError(
                            f"Expected elements in at {head} "
                            "but found empty list "
                            f"for template {'.'.join(path)}"
                        )
                    # Ensure the list is of dicts, and then recurse into
                    # each of the dict values.
                    if not all(isinstance(x, dict) for x in v):
                        raise TemplateError(
                            f"Expected list of dicts at key {head}, got {type(v)} "
                            f"for template {'.'.join(path)}"
                        )
                    values = [_fetch(x, tail, fail_if_not_found=True) for x in v]
                    if all([x is None for x in values]):
                        return None
                    if any([x is None for x in values]):
                        raise TemplateError(
                            f"Some elements at key {head}, "
                            f"did not return a template value "
                            f"for template {'.'.join(path)}"
                        )

                    return cast(List[TemplateValue], values)
                else:
                    raise ValueError(f"Expected dict at key {head}, got {type(v)}")
            else:
                if not (
                    isinstance(v, dict) or isinstance(v, list) or isinstance(v, str)
                ):
                    raise ValueError(
                        f"Expected final value at key {head}, got {type(v)}"
                    )
                else:
                    return v

    return _fetch(data, path, fail_if_not_found=strict)


def split_path(s: str) -> List[str]:
    """Splits a template value path to a list of parts.

    Anything in parentheses is considered a single part,
    even if it contains periods. E.g. "foo.bar(test.json).baz"
    will parse to ["foo", "bar(test.json)", "baz"]
    """
    paren_values: Dict[str, str] = {}
    new_str = s
    # Replace all strings within parentheses with a unique
    # identifier. These get replaced back after splitting
    # the path based on '.'. This prevents values within
    # parentheses that have periods (e.g. file paths) to
    # split incorrectly.
    for m in re.finditer(_PAREN_REGEX, s):
        part_id = uuid4().hex
        paren_values[part_id] = m.group(1)
        new_str = new_str.replace(m.group(1), part_id)
    result: List[str] = []
    for part in new_str.split("."):
        part = part.strip()
        for k, v in paren_values.items():
            part = part.replace(k, v)
        result.append(part)
    return result


def template_str(
    v: str, get_value: Callable[[List[str]], Optional[TemplateValue]]
) -> TemplateValue:
    new_v = v
    for m in re.finditer(
        TEMPLATE_REGEX,
        v,
    ):
        text = m.group(1)
        try:
            new_value = get_value(split_path(text))
            if new_value is not None:
                if isinstance(new_value, str):
                    new_v = new_v.replace(m.group(0), new_value)
                else:
                    # If the value is a dict or list, replace the
                    # entire string
                    return new_value
        except Exception as e:
            raise TemplateError(f"Error in template '{m.group(0)}': {e}") from e
    return new_v


def template_dict(
    d: Dict[str, Any],
    get_value: Callable[[List[str]], Optional[TemplateValue]],
) -> Dict[str, Any]:
    """Replaces dictionary with all secrets replaced with their values.

    get_value takes the list of strings that make up the template path
    and expects a string value. For example, ${{ output.file.path }}
    would call with ['output', 'file', 'path']. Return None if the
    value should not be replaced. Raise an exception if
    the template should exist but is not found or invalid.

    Template values are in the form ${{ secret.NAME }}
    """

    def _substitute(d: Dict[str, Any]) -> Dict[str, Any]:
        result: Dict[str, Any] = {}

        if isinstance(d, dict):
            for k, v in d.items():
                if isinstance(v, dict):
                    result[k] = _substitute(v)  # type: ignore
                elif isinstance(v, list):
                    new_list: List[Any] = []
                    for item in v:
                        if isinstance(item, dict):
                            new_list.append(_substitute(item))
                        elif isinstance(item, str):
                            new_list.append(template_str(item, get_value))
                        else:
                            new_list.append(item)
                    result[k] = new_list
                elif isinstance(v, str):
                    result[k] = template_str(v, get_value)
                else:
                    result[k] = v
        return result

    return _substitute(d)


def template_model(
    model: T,
    get_value: Callable[[List[str]], Optional[TemplateValue]],
) -> T:
    return model.__class__.parse_obj(template_dict(model.dict(), get_value))


class Templater(ABC):
    @abstractmethod
    def get_value(self, path: List[str]) -> Optional[TemplateValue]:
        pass

    def template_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return template_dict(data, self.get_value)

    def template_model(self, model: T) -> T:
        return template_model(model, self.get_value)


class MultiTemplater(Templater):
    def __init__(self, *templaters: Templater):
        self.templaters = templaters

    def get_value(self, path: List[str]) -> Optional[TemplateValue]:
        for t in self.templaters:
            v = t.get_value(path)
            if v is not None:
                return v
        return None


class DictTemplater(Templater):
    def __init__(self, data: Dict[str, Any], strict: bool = False):
        self.data = data
        self.strict = strict

    def get_value(self, path: List[str]) -> Optional[TemplateValue]:
        return find_value(self.data, path, self.strict)


class LocalTemplater(Templater):
    """Template values with local files.

    This allows users to template yaml with local values,
    like local paths. E.g., ${{ local.file("/path/to/file") }} will
    be replaced with the JSON content of the file at /path/to/file.
    """

    _FILE_REGEX: str = r"file\((.*)\)"
    _PATH_REGEX: str = r"path\((.*)\)"

    def __init__(self, base_dir: Optional[Union[str, Path]] = None) -> None:
        self.base_dir = Path(base_dir or Path.cwd())

    def get_value(self, path: List[str]) -> Optional[TemplateValue]:
        if path[0] == "local":
            path = path[1:]

            file_match = re.match(self._FILE_REGEX, path[0])
            if file_match:
                file_path = file_match.group(1)

                with open(self.base_dir / file_path) as f:
                    return json.load(f)

            path_match = re.match(self._PATH_REGEX, path[0])
            if path_match:
                file_path = Path(path_match.group(1))
                return str(self.base_dir / file_path)

        return None
