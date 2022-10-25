from pathlib import Path
from typing import Dict, Optional, Union

import yaml

from pctasks.core.utils.template import LocalTemplater
from pctasks.dataset.constants import DEFAULT_DATASET_YAML_PATH
from pctasks.dataset.models import DatasetDefinition


def template_dataset(
    yaml_str: str, parent_dir: Optional[Union[str, Path]] = None
) -> DatasetDefinition:
    dataset_dict = yaml.safe_load(yaml_str)
    if parent_dir:
        root = Path(parent_dir)
    else:
        root = Path.cwd()
    templater = LocalTemplater(root)
    dataset_dict = templater.template_dict(dataset_dict)
    return DatasetDefinition.parse_obj(dataset_dict)


def template_dataset_file(
    path: Optional[Union[str, Path]], args: Optional[Dict[str, str]] = None
) -> DatasetDefinition:
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

    dataset = template_dataset(p.read_text(), p.parent)
    if args:
        dataset = dataset.template_args(args)

    return dataset
