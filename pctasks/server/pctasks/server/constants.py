from opencensus.trace.attributes_helper import COMMON_ATTRIBUTES

# Headers containing information about the requester's
# IP address. Checked in the order listed here.
X_AZURE_CLIENTIP = "X-Azure-ClientIP"
X_ORIGINAL_FORWARDED_FOR = "X-Original-Forwarded-For"
X_FORWARDED_FOR = "X-Forwarded-For"

X_REQUEST_ENTITY = "X-PC-Request-Entity"
X_AZURE_REF = "X-Azure-Ref"
HEADER_REQUEST_ID = "request-id"

QS_REQUEST_ENTITY = "request_entity"

HTTP_429_TOO_MANY_REQUESTS = 429

HTTP_PATH = COMMON_ATTRIBUTES["HTTP_PATH"]
HTTP_URL = COMMON_ATTRIBUTES["HTTP_URL"]
HTTP_STATUS_CODE = COMMON_ATTRIBUTES["HTTP_STATUS_CODE"]
HTTP_METHOD = COMMON_ATTRIBUTES["HTTP_METHOD"]


class DIMENSION_KEYS:
    WORKFLOW_ID = "workflow"
    RUN_ID = "run_id"
    JOB_ID = "job_id"
    PARTITION_ID = "partition_id"
    TASK_ID = "task_id"

    REQUEST_IP = "request_ip"
    REQUEST_ID = "request_id"
    SUBSCRIPTION_KEY = "subscription_key"
    USER_EMAIL = "user_email"
    REQUEST_URL = "request_url"


SERVICE_NAME = "tasks"
