import logging
import sys
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Optional, Union

import click

from pctasks.cli.version import __version__
from pctasks.core.cli import get_plugin_subcommands
from pctasks.core.settings import SettingsError

logger = logging.getLogger(__name__)

PCTASKS_COMMAND_ENTRY_POINT_GROUP = "pctasks.commands"


def print_header() -> None:
    print(
        r"""
 ___   ___  _____            _
| _ \ / __||_   _| __ _  ___| |__ ___
|  _/| (__   | |  / _` |(_-/| / /(_-/
|_|   \___|  |_|  \__/_|/__/|_\_\/__/
"""
    )


class PCTasksGroup(click.Group):
    def format_help(self, ctx: Any, formatter: Any) -> Any:
        print_header()
        super().format_help(ctx, formatter)


@dataclass
class PCTasksCommandContext:
    profile: Optional[str] = None
    """Settings profile. Determines which settings file is read."""

    settings_file: Optional[str] = None
    """Full path to the settings file. If present, overrides the profile."""


@lru_cache(maxsize=1)
def _setup_logging(level: Union[str, int], log_libraries: bool = False) -> None:
    _logger = logging.root if log_libraries else logging.getLogger("pctasks")

    _logger.setLevel(level)

    if log_libraries:
        formatter = logging.Formatter("[%(levelname)s]:%(name)s: %(message)s")
    else:
        formatter = logging.Formatter("[%(levelname)s]:%(asctime)s: %(message)s")

    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(level)
    ch.setFormatter(formatter)
    _logger.addHandler(ch)


@click.group(name="pctasks", cls=PCTasksGroup)
@click.version_option(__version__)
@click.option("-v", "--verbose", help=("Use verbose mode"), is_flag=True)
@click.option("-q", "--quiet", help=("Use quiet mode (no output)"), is_flag=True)
@click.option(
    "-p",
    "--profile",
    help=("Settings profile. Determines which settings file is read."),
)
@click.option(
    "--settings-file",
    help=("Full path to the settings file. If present, overrides the profile."),
)
@click.pass_context
def pctasks_cmd(
    ctx: click.Context,
    verbose: bool,
    quiet: bool,
    profile: Optional[str],
    settings_file: Optional[str],
) -> None:
    print_header()
    logging_level = logging.INFO
    if verbose:
        logging_level = logging.DEBUG
    if quiet:
        logging_level = logging.ERROR

    ctx.obj = PCTasksCommandContext(profile=profile, settings_file=settings_file)

    _setup_logging(logging_level)


for subcommand in get_plugin_subcommands(
    click.Command, PCTASKS_COMMAND_ENTRY_POINT_GROUP
):
    pctasks_cmd.add_command(subcommand)


def cli() -> None:
    try:
        pctasks_cmd(prog_name="pctasks")
    except SettingsError as e:
        print(f"ERROR: {e}")
        if e.validation_error:
            print(
                """
Validation errors occurred.
Settings can be from the YAML configuration or the environment.
Hope this helps to debug:"""
            )
            print()
            msg = str(e.validation_error)
            msg = msg.replace("_Settings", "settings")
            print(msg)
            print()


if __name__ == "__main__":
    cli()
