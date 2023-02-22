from typing import Tuple

import click
from click.exceptions import Exit
from rich.console import Console
from rich.live import Live
from rich.table import Table

from pctasks.client.client import PCTasksClient
from pctasks.client.constants import NOT_FOUND_EXIT_CODE
from pctasks.client.settings import ClientSettings
from pctasks.client.utils import status_emoji
from pctasks.core.models.run import JobRunStatus
from pctasks.core.models.workflow import WorkflowRunStatus


def workflow_status_cmd(
    ctx: click.Context, run_id: str, watch: bool = False, poll_rate: int = 10
) -> int:
    """Show status of a workflow, including all jobs and tasks."""
    client = PCTasksClient(ClientSettings.from_context(ctx.obj))

    console = Console(stderr=True)

    table: Table
    is_complete: bool

    def status_entry(status: str) -> str:
        return f"{status_emoji(status)} {status.capitalize()}"

    def get_table() -> Tuple[Table, bool]:
        _table = Table()
        _table.add_column("")
        _table.add_column("status")
        workflow = client.get_workflow_run(run_id)
        if not workflow:
            console.print("[bold red]Workflow run not found.[/bold red]")
            raise Exit(NOT_FOUND_EXIT_CODE)
        wf_name = workflow.workflow_id

        _table.add_row(
            f"[bold]Workflow: {wf_name}[/bold]", status_entry(workflow.status)
        )

        def _job_status_sort(job_status: JobRunStatus) -> int:
            if job_status == JobRunStatus.RUNNING:
                return 0
            if job_status == JobRunStatus.FAILED:
                return 1
            if job_status == JobRunStatus.PENDING:
                return 2
            if job_status == JobRunStatus.COMPLETED:
                return 3
            if job_status == JobRunStatus.SKIPPED:
                return 4
            else:
                return 5

        for job in sorted(workflow.jobs, key=lambda x: _job_status_sort(x.status)):
            _table.add_row(
                f"  [bold]Job: {job.job_id}[/bold]", status_entry(job.status)
            )
            job_parts = client.list_job_partition_runs(run_id, job.job_id)
            for job_part in job_parts:
                _table.add_row(
                    f"    [bold]Partition: {job_part.partition_id}[/bold]",
                    status_entry(job_part.status),
                )
                for task in job_part.tasks:
                    _table.add_row(
                        f"      [bold]Task: {task.task_id}[/bold]",
                        status_entry(task.status),
                    )

        return (
            _table,
            workflow.status == WorkflowRunStatus.COMPLETED
            or workflow.status == WorkflowRunStatus.FAILED,
        )

    with console.status("Fetching records...") as fetch_status:
        fetch_status.update(
            status="[bold green]Fetching records...",
            spinner="aesthetic",
            spinner_style="green",
        )
        table, is_complete = get_table()

    if not watch:
        console.print(table)
    else:
        with Live(table, refresh_per_second=float(1 / poll_rate)) as live:
            while not is_complete:
                table, is_complete = get_table()
                live.update(table)

    return 0
