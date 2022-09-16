from typing import List, Optional

import click


@click.command("local")
@click.argument("workflow")
@click.option(
    "args",
    "-a",
    "--arg",
    multiple=True,
    help="Arguments to pass to the workflow. Formatted as 'key=value'",
)
@click.option("-o", "--output", help="URI of folder to write the task result to")
def local_cmd(workflow: str, args: List[str], output: Optional[str] = None) -> None:
    """Execute a workflow using a local runner.

    This executes a workflow sequentially and runs tasks
    in the local environment. Useful for testing.
    """
    from . import _cli

    return _cli.local_cmd(workflow, args, output=output)


@click.command("remote")
@click.argument("workflow")
@click.option(
    "args",
    "-a",
    "--arg",
    multiple=True,
    help="Arguments to pass to the workflow. Formatted as 'key=value'",
)
@click.option("--new-id", is_flag=True, help="Generate a new ID for the workflow")
@click.option("--settings", help="Base64 encoded settings to use")
@click.option("--sas", help="SAS token for reading workflow")
@click.pass_context
def remote_cmd(
    ctx: click.Context,
    workflow: str,
    args: List[str],
    new_id: bool,
    settings: Optional[str],
    sas: Optional[str],
) -> None:
    """Execute a workflow using a remote runner."""
    from . import _cli

    return _cli.remote_cmd(ctx, workflow, args, new_id, settings, sas)


@click.group("run")
@click.pass_context
def run_cmd(ctx: click.Context) -> None:
    """PCTasks commands for running workflows."""
    pass


run_cmd.add_command(local_cmd)
run_cmd.add_command(remote_cmd)
