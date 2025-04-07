from typing import Optional

from cachetools import cachedmethod

from pctasks.core.constants import DEFAULT_WEBHOOKS_TABLE_NAME
from pctasks.core.settings import PCTasksSettings
from pctasks.core.tables.registration import STACWebHookEventRegistrationTable


class TableNames:
    WEBHOOKS_TABLE_NAME: str = DEFAULT_WEBHOOKS_TABLE_NAME


class NotificationSettings(PCTasksSettings):
    @classmethod
    def section_name(cls) -> str:
        return "notifications"

    # Tables - used for downstream STAC event registrations
    tables_account_url: str
    tables_account_name: str
    tables_account_key: Optional[str] = None
    stac_webhooks_table_name: str = DEFAULT_WEBHOOKS_TABLE_NAME

    @cachedmethod(
        lambda self: self._cache,
        key=lambda self, target: (
            self.section_name(),
            DEFAULT_WEBHOOKS_TABLE_NAME,
            target,
        ),
    )
    def get_webhook_registration_table(self) -> STACWebHookEventRegistrationTable:
        return STACWebHookEventRegistrationTable.from_account_key(
            account_url=self.tables_account_url,
            account_name=self.tables_account_name,
            account_key=self.tables_account_key,
            table_name=self.stac_webhooks_table_name,
        )
