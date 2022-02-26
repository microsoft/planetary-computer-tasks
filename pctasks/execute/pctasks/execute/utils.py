def get_run_log_path(job_id: str, task_id: str, run_id: str) -> str:
    return f"logs/{job_id}/{task_id}/{run_id}/run.txt"


def get_exec_log_path(job_id: str, task_id: str, run_id: str) -> str:
    return f"logs/{job_id}/{task_id}/{run_id}/exec.txt"


def get_task_input_path(job_id: str, task_id: str, run_id: str) -> str:
    return f"run/{job_id}/{task_id}/{run_id}/input"


def get_task_output_path(job_id: str, task_id: str, run_id: str) -> str:
    return f"run/{job_id}/{task_id}/{run_id}/output"
