import re
from pathlib import Path
from typing import List, Optional, Union

import yaml
from planetary_computer.sas import get_token

from pctasks.core.utils.template import (
    LocalTemplater,
    MultiTemplater,
    Templater,
    TemplateValue,
)
from pctasks.dataset.constants import DEFAULT_DATASET_YAML_PATH
from pctasks.dataset.models import DatasetConfig


class PCTemplater(Templater):
    _GET_TOKEN_REGEX: str = r"get_token\(([^,]+),([^\)]+)\)"

    def get_value(self, path: List[str]) -> Optional[TemplateValue]:
        if path[0] != "pc":
            return None
        path = path[1:]

        get_token_match = re.match(self._GET_TOKEN_REGEX, path[0])
        if get_token_match:
            storage_account = get_token_match.group(1).strip()
            container = get_token_match.group(2).strip()
            return get_token(storage_account, container).token

        return None


def template_dataset(
    yaml_str: str, parent_dir: Optional[Union[str, Path]] = None
) -> DatasetConfig:
    workflow_dict = yaml.safe_load(yaml_str)
    if parent_dir:
        root = Path(parent_dir)
    else:
        root = Path.cwd()
    templater = MultiTemplater(LocalTemplater(root), PCTemplater())
    workflow_dict = templater.template_dict(workflow_dict)

    if "code" in workflow_dict:
        code = Path(workflow_dict["code"])
        if not code.is_absolute():
            code = str(root.joinpath(code).absolute())
            workflow_dict["code"] = str(code)
        
        if not Path(workflow_dict["code"]).exists():
            raise ValueError(f"Code file '{code}' does not exist.")

    return DatasetConfig.parse_obj(workflow_dict)


def template_dataset_file(
    path: Optional[Union[str, Path]],
) -> DatasetConfig:
    """Read and template a dataset YAML file.
    All local relative paths are relative to the file path.

    Args:
        path: The path to the dataset YAML file.

    Returns:
        The dataset model with template values.
    """
    if not path:
        path = DEFAULT_DATASET_YAML_PATH
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Dataset YAML file not found at '{p}'")

    return template_dataset(p.read_text(), p.parent)
