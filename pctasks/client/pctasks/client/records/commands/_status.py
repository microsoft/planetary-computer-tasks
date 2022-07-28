from typing import Optional, Tuple

import click
from click.exceptions import Exit
from rich.console import Console
from rich.live import Live
from rich.table import Table

from pctasks.client.client import PCTasksClient
from pctasks.client.errors import NotFoundError
from pctasks.client.records.constants import NOT_FOUND_EXIT_CODE
from pctasks.client.settings import ClientSettings
from pctasks.client.utils import status_emoji
from pctasks.core.models.workflow import WorkflowRunStatus


def workflow_status_cmd(
    ctx: click.Context, run_id: str, dataset: Optional[str], watch: bool = False
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
        try:
            workflow = client.get_workflow(run_id, dataset)
            wf_name = workflow.workflow.name if workflow.workflow else run_id
        except NotFoundError as e:
            console.print(f"[bold red]Workflow not found: {e}")
            raise Exit(NOT_FOUND_EXIT_CODE)

        _table.add_row(
            f"[bold]Workflow: {wf_name}[/bold]", status_entry(workflow.status)
        )

        for job in sorted(client.get_jobs(run_id), key=lambda j: j.created):
            _table.add_row(f" - Job: {job.job_id}", f" {status_entry(job.status)}")
            for task in sorted(
                client.get_tasks(run_id, job.job_id), key=lambda t: t.created
            ):
                _table.add_row(
                    f"    - Task:{task.task_id}", f"  {status_entry(task.status)}"
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
        with Live(table, refresh_per_second=1) as live:
            while not is_complete:
                table, is_complete = get_table()
                live.update(table)

    return 0
