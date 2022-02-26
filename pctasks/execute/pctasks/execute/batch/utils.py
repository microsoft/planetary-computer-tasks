import re
from datetime import datetime


def make_unique_job_id(job_id: str) -> str:
    return f"{job_id}-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"


def make_valid_batch_id(job_id: str) -> str:
    """Returns a job id or task id that is valid to Batch

    Note from Azure Batch SDK:

        Task ids can only contain any
        combination of alphanumeric characters along with dash (-)
        and underscore (_).
        The name must be from 1 through 64 characters long
    """
    return re.sub("[^a-zA-Z0-9_-]", "-", job_id)[-64:]
