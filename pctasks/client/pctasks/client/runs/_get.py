import click
from rich.console import Console

from pctasks.cli.cli import cli_output
from pctasks.client.client import PCTasksClient
from pctasks.client.constants import NOT_FOUND_EXIT_CODE
from pctasks.client.runs.utils import get_run_record
from pctasks.client.settings import ClientSettings


def get_workflow_run(ctx: click.Context, run_id: str, status_only: bool = False) -> int:
    """Fetch a workflow run record.

    Outputs the YAML of the record to stdout.
    """
    return get_run_record(
        ctx,
        lambda client, _: client.get_workflow_run(run_id),
        status_only=status_only,
    )


def get_workflow_log(
    ctx: click.Context,
    run_id: str,
) -> int:
    """Fetch a task record.

    Outputs the YAML of the record to stdout.
    """

    settings = ClientSettings.from_context(ctx.obj)
    client = PCTasksClient(settings)

    log_text = client.get_workflow_log(run_id)

    console = Console(stderr=True)
    if not log_text:
        console.print("[yellow]No log found.[/yellow]")
        return NOT_FOUND_EXIT_CODE

    console.print(f"\n[bold green]<LOG for workflow run {run_id}>[/bold green]")
    cli_output(log_text)
    console.print("[bold green]</LOG>[bold green]")

    return 0


def get_job_partition(
    ctx: click.Context,
    run_id: str,
    job_id: str,
    part_id: str,
    status_only: bool = False,
) -> int:
    """Fetch a job partition run record.

    Outputs the YAML of the record to stdout.
    """

    return get_run_record(
        ctx,
        lambda client, _: client.get_job_partition_run(
            run_id, job_id, partition_id=part_id
        ),
        status_only=status_only,
    )


def get_task_log(
    ctx: click.Context,
    run_id: str,
    job_id: str,
    partition_id: str,
    task_id: str,
) -> int:
    """Fetch a task record.

    Outputs the YAML of the record to stdout.
    """

    settings = ClientSettings.from_context(ctx.obj)
    client = PCTasksClient(settings)

    log_text = client.get_task_log(run_id, job_id, partition_id, task_id)

    console = Console(stderr=True)
    if not log_text:
        console.print("[yellow]No log found.[/yellow]")
        return NOT_FOUND_EXIT_CODE

    console.print(f"\n[bold green]<LOG for task {task_id}>[/bold green]")
    cli_output(log_text)
    console.print("[bold green]</LOG>[bold green]")

    return 0
