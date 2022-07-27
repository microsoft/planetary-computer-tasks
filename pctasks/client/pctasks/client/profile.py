from pathlib import Path
from typing import Optional

import click
import yaml
from pydantic import ValidationError
from rich import print as rprint
from rich.prompt import Confirm, Prompt

from pctasks.client.settings import ClientSettings
from pctasks.core.constants import DEFAULT_PROFILE, ENV_VAR_PCTASKS_PROFILE
from pctasks.core.settings import SettingsConfig
from pctasks.core.utils import map_opt


def _prompt_for_settings(existing: Optional[ClientSettings] = None) -> ClientSettings:
    endpoint = Prompt.ask(
        "Enter API endpoint", default=map_opt(lambda x: x.endpoint, existing)
    )
    if not endpoint:
        rprint("[yellow]No endpoint provided[/yellow]")
        raise click.Abort("No endpoint provided")
    api_key = Prompt.ask(
        "Enter API key", default=map_opt(lambda x: x.api_key, existing)
    )
    if not api_key:
        rprint("[yellow]No api key provided[/yellow]")
        raise click.Abort("No API key provided")
    default_conf = True
    if existing:
        default_conf = existing.confirmation_required
    confirmation_required = Confirm.ask(
        "Confirmation required?",
        default=default_conf,
    )
    return ClientSettings(
        endpoint=endpoint,
        api_key=api_key,
        confirmation_required=confirmation_required,
    )


@click.command(name="create")
@click.argument("profile")
@click.pass_context
def create_profile_command(ctx: click.Context, profile: str) -> None:
    """Creates a new profile based on prompted input"""
    settings_config = SettingsConfig.get(profile=profile)
    settings_file = settings_config.get_settings_file()
    if settings_file.exists():
        rprint(f"[red bold]Profile {profile} already exists[/red bold]")
        rprint("Use `pctasks profile edit` to edit the profile")
        ctx.exit(1)

    rprint(f"[green]Creating profile {profile}: [/green]")

    try:
        settings = _prompt_for_settings()
    except ValidationError as e:
        rprint("[red bold]Invalid settings![/red bold]")
        print(e)
        ctx.exit(2)

    settings_yaml = {settings.section_name(): settings.dict()}
    yaml_str = yaml.dump(settings_yaml, sort_keys=False)

    with open(settings_file, "w") as f:
        f.write(yaml_str)

    rprint(f"\n[green]Profile {profile} created![/green]")


@click.command(name="edit")
@click.argument("profile")
@click.pass_context
def edit_profile_command(ctx: click.Context, profile: str) -> None:
    """Modifies an existing profile based on prompted input"""
    settings_config = SettingsConfig.get(profile=profile)
    settings_file = settings_config.get_settings_file()
    if not settings_file.exists():
        rprint(f"[red bold]Profile {profile} does not exists[/red bold]")
        rprint("Use `pctasks profile create` to create the profile")
        ctx.exit(1)

    exisiting_settings = ClientSettings.get(settings_file=settings_file)

    rprint(f"[green]Editing profile {profile}: [/green]")

    try:
        settings = _prompt_for_settings(exisiting_settings)
    except ValidationError as e:
        rprint("[red bold]Invalid settings![/red bold]")
        print(e)
        ctx.exit(2)

    settings_yaml = {settings.section_name(): settings.dict()}
    yaml_str = yaml.dump(settings_yaml, sort_keys=False)

    with open(settings_file, "w") as f:
        f.write(yaml_str)

    rprint(f"\n[green]Profile {profile} updated![/green]")


@click.command(name="set")
@click.argument("profile")
def set_profile_command(profile: str) -> None:
    """Sets the profile to be used by pctasks.

    The profile set by this command can still be overridden by the
    environment variable PCTASKS_PROFILE or by command line options.
    """
    settings_config = SettingsConfig.get(profile=profile)
    profile_only_config = settings_config.copy(update={"settings_file": None})
    profile_settings_file = profile_only_config.get_settings_file()
    if not Path(profile_settings_file).exists():
        raise click.UsageError(
            f"Settings file for profile '{profile}' "
            f"does not exist at location {profile_settings_file}."
        )
    settings_config.write()
    rprint(f"[green]Profile now set to [/green][bold]{profile}[/bold]")
    print()


@click.command(name="get")
def get_profile_command() -> None:
    """Gets the profile that has been set to be used by pctasks."""
    settings_config = SettingsConfig.get()
    if settings_config.is_profile_from_environment:
        rprint(
            f"[green]Profile set to[/green] [bold]{settings_config.profile}[/bold] "
            "[italics]through the "
            f"environment variable {ENV_VAR_PCTASKS_PROFILE}[/italics]"
        )
        print()
    else:
        if (
            settings_config.profile is None
            or settings_config.profile == DEFAULT_PROFILE
        ):
            rprint("[yellow]No profile set.[/yellow]")
            print()
        else:
            rprint(
                f"[green]Profile set to[/green] [bold]{settings_config.profile}[/bold]"
            )
            print()


@click.group(name="profile")
def profile_cmd() -> None:
    pass


profile_cmd.add_command(create_profile_command)
profile_cmd.add_command(edit_profile_command)
profile_cmd.add_command(set_profile_command)
profile_cmd.add_command(get_profile_command)
