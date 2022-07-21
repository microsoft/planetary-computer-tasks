import logging
from pathlib import Path
import sys
from functools import lru_cache
from typing import Any, Optional, Union

import click

from pctasks.cli.version import __version__
from pctasks.core.cli import get_plugin_subcommands
from pctasks.core.constants import DEFAULT_PROFILE, ENV_VAR_PCTASKS_PROFILE
from pctasks.core.context import PCTasksCommandContext
from pctasks.core.settings import SettingsConfig, SettingsError

logger = logging.getLogger(__name__)

PCTASKS_COMMAND_ENTRY_POINT_GROUP = "pctasks.commands"


def cli_print(msg: str = "", nl: bool = True) -> None:
    """Print messages to the console.

    Uses stderr, avoiding stdout which should only
    be used for data output that can be piped to other
    commands.
    """
    click.echo(msg, err=True, nl=nl)


def cli_output(output: str) -> None:
    """Send output to stdout.

    Use for CLI output that can be piped into other commands.
    """
    print(output)


def print_header() -> None:
    cli_print(
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


@lru_cache(maxsize=1)
def setup_logging(level: Union[str, int], log_libraries: bool = False) -> None:
    _logger = logging.root if log_libraries else logging.getLogger("pctasks")

    _logger.setLevel(level)

    if log_libraries:
        formatter = logging.Formatter("[%(levelname)s]:%(name)s: %(message)s")
    else:
        formatter = logging.Formatter("[%(levelname)s]:%(asctime)s: %(message)s")

    ch = logging.StreamHandler(sys.stderr)
    ch.setLevel(level)
    ch.setFormatter(formatter)
    _logger.addHandler(ch)


@lru_cache()
def setup_logging_for_module(
    package: str, level: Union[str, int], log_libraries: bool = False
) -> None:
    _logger = logging.getLogger(package)

    _logger.setLevel(level)

    if log_libraries:
        formatter = logging.Formatter("[%(levelname)s]:%(name)s: %(message)s")
    else:
        formatter = logging.Formatter("[%(levelname)s]:%(asctime)s: %(message)s")

    ch = logging.StreamHandler(sys.stderr)
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
    help=(
        "Settings profile. Determines which settings file is read. "
        "You can also set the PCTASKS_PROFILE environment variable to "
        "control the default profile."
    ),
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

    setup_logging(logging_level)


@click.command(name="set-profile")
@click.argument("profile")
def set_profile_command(profile: str) -> None:
    settings_config = SettingsConfig.get(profile=profile)
    profile_only_config = settings_config.copy(update={"settings_file": None})
    profile_settings_file = profile_only_config.get_settings_file()
    if not Path(profile_settings_file).exists():
        raise click.UsageError(
            f"Settings file for profile '{profile}' "
            f"does not exist at location {profile_settings_file}."
        )
    settings_config.write()
    cli_print(f"Profile set to '{profile}'.")


@click.command(name="get-profile")
def get_profile_command() -> None:
    settings_config = SettingsConfig.get()
    if settings_config.is_profile_from_environment:
        cli_print(
            f"Profile set to '{settings_config.profile}' through the "
            f"environment variable {ENV_VAR_PCTASKS_PROFILE}."
        )
    else:
        if (
            settings_config.profile is None
            or settings_config.profile == DEFAULT_PROFILE
        ):
            cli_print("No profile set.")
        else:
            cli_print(f"Profile set to '{settings_config.profile}'.")


pctasks_cmd.add_command(set_profile_command)
pctasks_cmd.add_command(get_profile_command)

for subcommand in get_plugin_subcommands(
    click.Command, PCTASKS_COMMAND_ENTRY_POINT_GROUP
):
    pctasks_cmd.add_command(subcommand)


def cli() -> None:
    try:
        pctasks_cmd(prog_name="pctasks")
    except SettingsError as e:
        cli_print(f"ERROR: {e}")
        if e.validation_error:
            cli_print(
                """
Validation errors occurred.
Settings can be from the YAML configuration or the environment.
Hope this helps to debug:"""
            )
            cli_print()
            msg = str(e.validation_error)
            msg = msg.replace("_Settings", "settings")
            cli_print(msg)
            cli_print()


if __name__ == "__main__":
    cli()
