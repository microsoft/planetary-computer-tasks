import click


@click.group(name="profile")
def profile_cmd() -> None:
    pass


@profile_cmd.command(name="create")
@click.argument("profile")
@click.pass_context
def create_profile_command(ctx: click.Context, profile: str) -> None:
    """Creates a new profile based on prompted input"""
    from .commands import create_profile

    create_profile(ctx, profile)


@profile_cmd.command(name="edit")
@click.argument("profile")
@click.pass_context
def edit_profile_command(ctx: click.Context, profile: str) -> None:
    """Modifies an existing profile based on prompted input"""
    from .commands import edit_profile

    edit_profile(ctx, profile)


@profile_cmd.command(name="set")
@click.argument("profile")
@click.pass_context
def set_profile_command(ctx: click.Context, profile: str) -> None:
    """Sets the profile to be used by pctasks.

    The profile set by this command can still be overridden by the
    environment variable PCTASKS_PROFILE or by command line options.
    """
    from .commands import set_profile

    set_profile(ctx, profile)


@profile_cmd.command(name="show")
@click.argument("profile")
@click.pass_context
def show_profile_command(ctx: click.Context, profile: str) -> None:
    """Shows the values of the settings for PROFILE"""
    from .commands import show_profile

    show_profile(ctx, profile)


@profile_cmd.command(name="get")
def get_profile_command() -> None:
    """Gets the profile that has been set to be used by pctasks."""
    from .commands import get_profile

    get_profile()


@profile_cmd.command(name="list")
def list_profiles_command() -> None:
    """Lists all available profiles."""
    from .commands import list_profiles

    list_profiles()
