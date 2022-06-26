from pathlib import Path
from typing import Any, Dict, Union

import yaml

from pctasks.core.models.workflow import WorkflowConfig
from pctasks.core.utils.template import LocalTemplater


def template_workflow_dict(
    workflow_dict: Dict[str, Any],
    base_path: Union[str, Path] = Path.cwd(),
) -> WorkflowConfig:
    """Read and template a workflow dict.
    All local relative paths are relative to base_path

    Args:
        workflow_dict: The workflow dict.

    Returns:
        The workflow model with template values.
    """
    workflow_dict = LocalTemplater(base_path).template_dict(workflow_dict)

    return WorkflowConfig.parse_obj(workflow_dict)


def template_workflow_file(
    path: Union[str, Path],
) -> WorkflowConfig:
    """Read and template a workflow file.
    All local relative paths are relative to the file path.

    Args:
        path: The path to the workflow file.

    Returns:
        The workflow model with template values.
    """
    p = Path(path)
    workflow_dict = yaml.safe_load(p.read_text())

    return template_workflow_dict(workflow_dict, p.parent)
