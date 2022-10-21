class PCTasksError(Exception):
    """Base class for all PCTasks errors."""

    pass


class NotFoundError(PCTasksError):
    """Raised when a record is not found."""

    pass


class WorkflowRunNotFoundError(NotFoundError):
    """Raised when a workflow run is not found."""

    pass


class WorkflowNotFoundError(NotFoundError):
    """Raised when a workflow is not found."""

    pass


class WorkflowExistsError(NotFoundError):
    """Raised when a workflow exists when it is not expected."""

    pass


class JobPartitionRunNotFoundError(NotFoundError):
    """Raised when a job is not found."""

    pass


class ConfirmationError(Exception):
    pass


class NoWorkflowIDError(Exception):
    pass
