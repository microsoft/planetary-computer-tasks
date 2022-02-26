from cachetools import cachedmethod

from pctasks.core.constants import DEFAULT_DATASET_TABLE_NAME
from pctasks.core.settings import PCTasksSettings
from pctasks.core.tables.dataset import DatasetIdentifierTable


class OperationsSettings(PCTasksSettings):
    @classmethod
    def section_name(cls) -> str:
        return "ops"

    # Tables - used for blob event registrations (source eventing)
    tables_account_url: str
    tables_account_name: str
    tables_account_key: str

    # Dataset
    dataset_table_name: str = DEFAULT_DATASET_TABLE_NAME

    @cachedmethod(
        lambda self: self._settings_cache,
        key=lambda self: (
            self.section_name(),
            DEFAULT_DATASET_TABLE_NAME,
        ),
    )
    def get_dataset_table(self) -> DatasetIdentifierTable:
        return DatasetIdentifierTable.from_account_key(
            account_url=self.tables_account_url,
            account_name=self.tables_account_name,
            account_key=self.tables_account_key,
            table_name=self.dataset_table_name,
        )
