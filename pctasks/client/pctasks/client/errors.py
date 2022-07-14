class PCTasksError(Exception):
    """Base class for all PCTasks errors."""

    pass


class NotFoundError(PCTasksError):
    """Raised when a record is not found."""

    pass


class WorkflowNotFoundError(NotFoundError):
    """Raised when a workflow is not found."""

    pass


class JobNotFoundError(NotFoundError):
    """Raised when a job is not found."""

    pass


class TaskNotFoundError(NotFoundError):
    """Raised when a task is not found."""

    pass
