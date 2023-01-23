from typing import Optional

import click


@click.command("status")
@click.argument("run_id", required=False)
@click.option(
    "-w",
    "--watch",
    is_flag=True,
    help=(
        "Watch the status of the workflow, refreshing every 10 seconds. "
        "or the rate determined by --poll-rate"
    ),
)
@click.option("-r", "--poll-rate", type=int, default=10, help="Poll rate in seconds")
@click.pass_context
def status_cmd(
    ctx: click.Context, run_id: Optional[str], watch: bool, poll_rate: int
) -> None:
    """Fetch a workflow status

    RUN_ID can be supplied as a command line argument or as stdin.
    """
    from . import _status

    if run_id is None or run_id == "-":
        run_id = click.get_text_stream("stdin").read()
    if not run_id:
        raise click.UsageError("Missing RUN_ID")

    ctx.exit(_status.workflow_status_cmd(ctx, run_id, watch=watch, poll_rate=poll_rate))
