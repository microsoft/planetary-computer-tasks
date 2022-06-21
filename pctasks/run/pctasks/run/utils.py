def get_run_log_path(job_id: str, task_id: str, run_id: str) -> str:
    return f"logs/{run_id}/{job_id}/{task_id}/run.txt"


def get_exec_log_path(job_id: str, task_id: str, run_id: str) -> str:
    return f"logs/{run_id}/{job_id}/{task_id}/exec.txt"


def get_task_input_path(job_id: str, task_id: str, run_id: str) -> str:
    return f"run/{run_id}/{job_id}/{task_id}/input"


def get_task_output_path(job_id: str, task_id: str, run_id: str) -> str:
    return f"run/{run_id}/{job_id}/{task_id}/output"


def get_workflow_path(run_id: str) -> str:
    return f"run/{run_id}/workflow.yaml"
