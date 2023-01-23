class WorkflowFailedError(Exception):
    pass


class TaskFailedError(Exception):
    pass


class TaskPreparationError(Exception):
    pass


class WorkflowRunRecordError(Exception):
    """Raised when there are unexpected results or behaviors from run records"""

    pass
