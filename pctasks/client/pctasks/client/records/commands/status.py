from typing import Optional

import click


@click.command("workflow")
@click.argument("run_id", required=False)
@click.option(
    "-w",
    "--watch",
    is_flag=True,
    help="Watch the status of the workflow, refreshing every second",
)
@click.pass_context
def workflow_status_cmd(ctx: click.Context, run_id: Optional[str], watch: bool) -> None:
    """Fetch a workflow status

    RUN_ID can be supplied as a command line argument or as stdin.
    """
    from . import _status

    if run_id is None or run_id == "-":
        run_id = click.get_text_stream("stdin").read()
    if not run_id:
        raise click.UsageError("Missing RUN_ID")

    ctx.exit(_status.workflow_status_cmd(ctx, run_id, watch))


@click.group("status")
def status_cmd() -> None:
    """Fetch a workflow status."""
    pass


status_cmd.add_command(workflow_status_cmd)
