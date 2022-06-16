import os


class EnvironmentConfigError(Exception):
    pass


def get_dev_env(key: str) -> str:
    result = os.environ.get(key)
    if not result:
        raise EnvironmentConfigError(
            f"Missing environment variable: {key}. "
            "Make sure your development environment has "
            "all of the necessary Azurite environment variables. "
            "Check the package README for a complete list."
        )
    return result


# Queues

PCTASKS_QUEUES_ACCOUNT_URL_ENV_VAR = "PCTASKS_RUN__QUEUES_ACCOUNT_URL"
PCTASKS_QUEUES_ACCOUNT_NAME_ENV_VAR = "PCTASKS_RUN__QUEUES_ACCOUNT_NAME"
PCTASKS_QUEUES_ACCOUNT_KEY_ENV_VAR = "PCTASKS_RUN__QUEUES_ACCOUNT_KEY"

# Tables

PCTASKS_TABLES_ACCOUNT_URL_ENV_VAR = "PCTASKS_RUN__TABLES_ACCOUNT_URL"
PCTASKS_TABLES_ACCOUNT_NAME_ENV_VAR = "PCTASKS_RUN__TABLES_ACCOUNT_NAME"
PCTASKS_TABLES_ACCOUNT_KEY_ENV_VAR = "PCTASKS_RUN__TABLES_ACCOUNT_KEY"

# Blob

PCTASKS_BLOB_ACCOUNT_URL_ENV_VAR = "PCTASKS_RUN__BLOB_ACCOUNT_URL"
PCTASKS_BLOB_ACCOUNT_NAME_ENV_VAR = "PCTASKS_RUN__BLOB_ACCOUNT_NAME"
PCTASKS_BLOB_ACCOUNT_KEY_ENV_VAR = "PCTASKS_RUN__BLOB_ACCOUNT_KEY"
