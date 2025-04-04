from typing import Optional

from cachetools import cachedmethod

from pctasks.core.constants import (
    DEFAULT_BLOB_TRIGGER_REGISTRATION_TABLE_NAME,
    DEFAULT_NOTIFICATIONS_QUEUE_NAME,
    DEFAULT_WORKFLOW_QUEUE_NAME,
)
from pctasks.core.settings import PCTasksSettings
from pctasks.core.tables.registration import BlobTriggerEventRegistrationTable


class RouterSettings(PCTasksSettings):
    @classmethod
    def section_name(cls) -> str:
        return "router"

    # Queues
    queues_connection_string: str
    workflow_queue_name: str = DEFAULT_WORKFLOW_QUEUE_NAME
    notification_queue_name: str = DEFAULT_NOTIFICATIONS_QUEUE_NAME

    # Tables - used for blob event registrations (source eventing)
    tables_account_url: str
    tables_account_name: str
    tables_account_key: Optional[str] = None
    blob_trigger_registration_table_name: str = (
        DEFAULT_BLOB_TRIGGER_REGISTRATION_TABLE_NAME
    )

    @cachedmethod(
        lambda self: self._settings_cache,
        key=lambda self: (
            self.section_name(),
            DEFAULT_BLOB_TRIGGER_REGISTRATION_TABLE_NAME,
        ),
    )
    def get_blob_trigger_registration_table(self) -> BlobTriggerEventRegistrationTable:
        return BlobTriggerEventRegistrationTable.from_account_key(
            account_url=self.tables_account_url,
            account_name=self.tables_account_name,
            account_key=self.tables_account_key,
            table_name=self.blob_trigger_registration_table_name,
        )
