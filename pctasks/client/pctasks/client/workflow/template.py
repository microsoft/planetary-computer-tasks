from pathlib import Path
from typing import Any, Dict, Optional, Union

import yaml

from pctasks.core.models.workflow import WorkflowDefinition
from pctasks.core.utils.template import LocalTemplater


def template_workflow_dict(
    workflow_dict: Dict[str, Any], base_path: Optional[Union[str, Path]] = None
) -> WorkflowDefinition:
    """Read and template a workflow dict.
    All local relative paths are relative to base_path

    Args:
        workflow_dict: The workflow dict.
        base_path: The base path to use for relative paths.
            Defaults to the current directory.

    Returns:
        The workflow model with template values.
    """
    base_path = base_path or Path(".")

    if "args" in workflow_dict and isinstance(workflow_dict["args"], dict):
        workflow_dict["args"] = list(workflow_dict["args"].keys())

    workflow_dict = LocalTemplater(base_path).template_dict(workflow_dict)

    return WorkflowDefinition.model_validate(workflow_dict)


def template_workflow_contents(
    contents: str, base_path: Optional[Union[str, Path]] = None
) -> WorkflowDefinition:
    """Read and template a workflow file contents.
    All local relative paths are relative to base_path

    Args:
        path: The path to the workflow file.
        base_path: The base path to use for relative paths.
            Defaults to the current directory.

    Returns:
        The workflow model with template values.
    """
    workflow_dict = yaml.safe_load(contents)

    return template_workflow_dict(workflow_dict, base_path)


def template_workflow_file(
    path: Union[str, Path],
) -> WorkflowDefinition:
    """Read and template a workflow file.
    All local relative paths are relative to the file path.

    Args:
        path: The path to the workflow file.

    Returns:
        The workflow model with template values.
    """
    p = Path(path)
    return template_workflow_contents(p.read_text(), p.parent)
