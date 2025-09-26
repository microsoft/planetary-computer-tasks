import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import azure.batch.models as batchmodels

from pctasks.run.batch.utils import make_valid_batch_id

logger = logging.getLogger(__name__)


@dataclass
class BatchTask:
    task_id: str
    command: List[str]
    """A command list to be executed by this batch task."""

    image: str
    """The image to use for this task."""

    environ: Optional[Dict[str, str]] = None
    """Optional list of environment variables to
    inject into the container"""

    workdir: Optional[str] = None
    """If set, the docker will be run with this as the
    working directory"""

    def _get_command(self) -> Tuple[str, str]:
        run_opts = "--rm"
        if self.environ is not None:
            for key, value in self.environ.items():
                run_opts += f" -e {key}={value} "
        if self.workdir is not None:
            run_opts += f" -w {self.workdir} "

        # Anything that would create shell errors.
        def _escape_arg(arg: str) -> str:
            for escape_char in ["&", "+", "$", "\\"]:
                if escape_char in arg:
                    arg = f'"{arg}"'
                    break
            return arg

        # Ignoring types because mypy is confused about get_command not
        # being a class method

        cmds = [_escape_arg(arg) for arg in self.command]

        return (run_opts, " ".join(cmds))

    def to_params(self) -> batchmodels.BatchTaskCreateContent:
        task_id = make_valid_batch_id(self.task_id)

        container_run_options, task_command = self._get_command()

        task_container_settings = batchmodels.BatchTaskContainerSettings(
            image_name=self.image
        )
        task_container_settings.container_run_options = container_run_options

        return batchmodels.BatchTaskCreateContent(
            id=task_id,
            command_line=task_command,
            container_settings=task_container_settings,
        )
