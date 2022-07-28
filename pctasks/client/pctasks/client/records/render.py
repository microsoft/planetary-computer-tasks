from typing import Any, Dict, List

import pandas as pd
from rich.console import Console

from pctasks.client.records.console.dataframe import DataFrameRender
from pctasks.client.utils import status_emoji
from pctasks.core.models.api import JobRunResponse, TaskRunResponse, WorkflowRunResponse


def workflows_to_df(workflows: List[WorkflowRunResponse]) -> pd.DataFrame:
    rows: List[Dict[str, Any]] = []
    for wf in workflows:
        d = wf.dict()
        d["dataset"] = str(wf.dataset)
        rows.append(d)
    return pd.DataFrame(rows)


def render_workflows(
    console: Console,
    workflows: List[WorkflowRunResponse],
    page_results: bool = False,
    show_all: bool = False,
) -> None:
    if not workflows:
        console.print("No workflows found!", style="bold red")
        return
    df = workflows_to_df(workflows)
    df["emoji"] = df.apply(lambda row: status_emoji(row["status"]), axis=1)
    columns = ["emoji", "run_id", "status", "created"]
    df = df.copy()[columns].reset_index().drop("index", axis=1)
    df = df.sort_values(by=["created"], ascending=False)
    DataFrameRender(console, df, all=show_all).render(page=page_results)


def jobs_to_df(jobs: List[JobRunResponse]) -> pd.DataFrame:
    rows: List[Dict[str, Any]] = []
    for j in jobs:
        d = j.dict()
        rows.append(d)
    return pd.DataFrame(rows)


def render_jobs(
    console: Console,
    jobs: List[JobRunResponse],
    page_results: bool = False,
    show_all: bool = False,
) -> None:
    if not jobs:
        console.print("No jobs found!", style="bold red")
        return
    df = jobs_to_df(jobs)
    df["emoji"] = df.apply(lambda row: status_emoji(row["status"]), axis=1)
    columns = ["emoji", "job_id", "status", "created"]
    df = df.copy()[columns].reset_index().drop("index", axis=1)
    df = df.sort_values(by=["created"], ascending=False)
    DataFrameRender(console, df, all=show_all).render(page=page_results)


def tasks_to_df(tasks: List[TaskRunResponse]) -> pd.DataFrame:
    rows: List[Dict[str, Any]] = []
    for task in tasks:
        d = task.dict()
        rows.append(d)
    return pd.DataFrame(rows)


def render_tasks(
    console: Console,
    tasks: List[TaskRunResponse],
    page_results: bool = False,
    show_all: bool = False,
) -> None:
    if not tasks:
        console.print("No tasks found!", style="bold red")
        return
    df = tasks_to_df(tasks)
    df["emoji"] = df.apply(lambda row: status_emoji(row["status"]), axis=1)
    columns = ["emoji", "task_id", "status", "created"]
    df = df.copy()[columns].reset_index().drop("index", axis=1)
    df = df.sort_values(by=["created"], ascending=False)
    DataFrameRender(console, df, all=show_all).render(page=page_results)
