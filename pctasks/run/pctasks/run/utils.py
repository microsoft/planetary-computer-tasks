from uuid import uuid1


def get_workflow_path(run_id: str) -> str:
    return f"run/{run_id}/workflow.yaml"


def get_workflow_log_path(run_id: str) -> str:
    return f"logs/{run_id}/workflow-run-log.txt"


def get_task_log_path(job_id: str, partition_id: str, task_id: str, run_id: str) -> str:
    return f"logs/{run_id}/{job_id}/{partition_id}/{task_id}/task-log.txt"


def get_task_input_path(
    job_id: str, partition_id: str, task_id: str, run_id: str
) -> str:
    return f"run/{run_id}/{job_id}/{partition_id}/{task_id}/input"


def get_task_output_path(
    job_id: str, partition_id: str, task_id: str, run_id: str
) -> str:
    return f"run/{run_id}/{job_id}/{partition_id}/{task_id}/output"


def get_task_status_path(
    job_id: str, partition_id: str, task_id: str, run_id: str
) -> str:
    return (
        f"status/{run_id}/{job_id}/{partition_id}/{task_id}/"
        f"status-{uuid1().hex[:5]}.txt"
    )
