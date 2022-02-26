from pathlib import Path
from typing import Union

import yaml

from pctasks.core.models.workflow import WorkflowConfig
from pctasks.core.utils.template import LocalTemplater


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
    workflow_dict = LocalTemplater(p.parent).template_dict(workflow_dict)

    return WorkflowConfig.parse_obj(workflow_dict)
