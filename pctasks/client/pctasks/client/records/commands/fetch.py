from typing import Optional

import click


@click.command("workflow")
@click.argument("run_id")
@click.option("-d", "--dataset", help="Filter by dataset.")
@click.pass_context
def fetch_workflow_cmd(
    ctx: click.Context,
    run_id: str,
    dataset: Optional[str],
) -> int:
    """Fetch a workflow record.

    Outputs the YAML of the record to stdout.
    """
    from . import _fetch

    return _fetch.fetch_workflow_cmd(ctx, run_id, dataset)


@click.command("job")
@click.argument("run_id")
@click.argument("job_id")
@click.pass_context
def fetch_job_cmd(
    ctx: click.Context,
    run_id: str,
    job_id: str,
) -> int:
    """Fetch a job record.

    Outputs the YAML of the record to stdout.
    """
    from . import _fetch

    return _fetch.fetch_job_cmd(ctx, run_id, job_id)


@click.command("task")
@click.argument("run_id")
@click.argument("job_id")
@click.argument("task_id")
@click.pass_context
def fetch_task_cmd(
    ctx: click.Context,
    run_id: str,
    job_id: str,
    task_id: str,
) -> int:
    """Fetch a task record.

    Outputs the YAML of the record to stdout.
    """
    from . import _fetch

    return _fetch.fetch_task_cmd(ctx, run_id, job_id, task_id)


@click.command("logs")
@click.argument("run_id")
@click.argument("job_id")
@click.argument("task_id")
@click.option("--name", "-n", help="Filter by log name.")
@click.pass_context
def fetch_logs_cmd(
    ctx: click.Context, job_id: str, task_id: str, run_id: str, name: Optional[str]
) -> int:
    """Fetch a task record.

    Outputs the YAML of the record to stdout.
    """
    from . import _fetch

    return _fetch.fetch_logs_cmd(ctx, job_id, task_id, run_id, name)


@click.group("fetch")
def fetch_cmd() -> None:
    """Fetch a record, logs or events."""
    pass


fetch_cmd.add_command(fetch_workflow_cmd)
fetch_cmd.add_command(fetch_job_cmd)
fetch_cmd.add_command(fetch_task_cmd)
fetch_cmd.add_command(fetch_logs_cmd)
