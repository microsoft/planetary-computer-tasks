class OrchestratorNames:
    WORKFLOW = "WorkflowOrch"
    JOB = "JobOrch"
    TASK = "TaskOrch"
    TASK_POLL = "TaskPollOrch"
    NOTIFY = "NotifyOrch"


class ActivityNames:
    ORCH_SIGNAL = "OrchSignalAct"
    ORCH_CANCEL = "OrchCancelAct"
    ORCH_FETCH_STATUS = "OrchFetchStatusAct"
    JOB_SEND_NOTIFICATION = "JobSendNotificationAct"
    TASK_SUBMIT = "TaskSubmitAct"
    TASK_POLL = "TaskPollAct"
    TASK_HANDLE_RESULT = "TaskHandleResultAct"
    NOTIFY_FETCH = "NotifyFetchAct"
    NOTIFY_EG = "NotifyEventGridAct"
    NOTIFY_WEBHOOK = "NotifyWebHookAct"
    UPDATE_RECORD = "UpdateRecordAct"


class StarterNames:
    WORKFLOW = "WorkflowStart"
    NOTIFY = "NotifyStart"


class FunctionNames:
    TASK_SIGNAL = "TaskSignal"
    OPERATION_HANDLER = "OperationHandler"


class EventNames:
    TASK_SIGNAL = "TaskSignal"
    POLL_QUIT = "PollQuit"
    CANCEL = "Cancel"


MAX_MISSING_POLLS = 5

# Template paths

JOBS_TEMPLATE_PATH = "jobs"
TASKS_TEMPLATE_PATH = "tasks"
TRIGGER_TEMPLATE_PATH = "trigger"
ARGS_TEMPLATE_PATH = "args"
ITEM_TEMPLATE_PATH = "item"
