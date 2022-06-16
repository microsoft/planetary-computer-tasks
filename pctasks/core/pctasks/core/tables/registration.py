import re
from abc import ABC, abstractmethod
from typing import Generic, List, Optional, TypeVar

from pctasks.core.constants import DEFAULT_TARGET_ENVIRONMENT
from pctasks.core.models.event import CloudEvent, NotificationMessage
from pctasks.core.models.registration import (
    BlobTriggerEventRegistration,
    EventRegistration,
    STACItemEventRegistration,
)
from pctasks.core.tables.base import ModelTableService

T = TypeVar("T", bound=EventRegistration)

STORAGE_ACCOUNT_REGEX = ".*/Microsoft.Storage/storageAccounts/([^/]+)$"
CONTAINER_REGEX = "^/blobServices/default/containers/([^/]+)/.*"


class CloudEventRegistrationTableService(Generic[T], ModelTableService[T], ABC):
    @abstractmethod
    def _get_partition_key_from_registration(self, registration: T) -> str:
        pass

    @abstractmethod
    def get_registration_key(self, event: CloudEvent) -> Optional[str]:
        """Gets a registration key from the given event.

        This partition key can be used in the get_registrations call.
        If None is return, the event does not match the type of registrations
        this table holds.
        """
        pass

    def insert_record(self, registration: T) -> None:
        self.insert(
            partition_key=self._get_partition_key_from_registration(registration),
            row_key=registration.id,
            entity=registration,
        )

    def upsert_record(self, registration: T) -> None:
        self.upsert(
            partition_key=self._get_partition_key_from_registration(registration),
            row_key=registration.id,
            entity=registration,
        )

    def update_record(self, registration: T) -> None:
        self.update(
            partition_key=self._get_partition_key_from_registration(registration),
            row_key=registration.id,
            entity=registration,
        )

    def get_registrations(self, registration_key: str) -> List[T]:
        """Gets the registrations for the given registration key.

        Use get_registration_key to get the key from an event.
        """
        return self.query(f"PartitionKey eq '{registration_key}'")


class NotificationRegistrationTableService(Generic[T], ModelTableService[T], ABC):
    @abstractmethod
    def _get_partition_key_from_registration(
        self, registration: T, target_environment: Optional[str]
    ) -> str:
        pass

    @abstractmethod
    def get_registration_key(
        self, notification: NotificationMessage, target_environment: Optional[str]
    ) -> Optional[str]:
        """Gets a registration key from the given notification message.

        This partition key can be used in the get_registrations call.
        If None is return, the notification does not match the type of registrations
        this table holds.
        """
        pass

    def insert_record(self, registration: T, target_environment: Optional[str]) -> None:
        self.insert(
            partition_key=self._get_partition_key_from_registration(
                registration, target_environment
            ),
            row_key=registration.id,
            entity=registration,
        )

    def upsert_record(self, registration: T, target_environment: Optional[str]) -> None:
        self.upsert(
            partition_key=self._get_partition_key_from_registration(
                registration, target_environment
            ),
            row_key=registration.id,
            entity=registration,
        )

    def update_record(self, registration: T, target_environment: Optional[str]) -> None:
        self.update(
            partition_key=self._get_partition_key_from_registration(
                registration, target_environment
            ),
            row_key=registration.id,
            entity=registration,
        )

    def get_registrations(self, registration_key: str) -> List[T]:
        """Gets the registrations for the given registration key.

        Use get_registration_key to get the key from an event.
        """
        return self.query(f"PartitionKey eq '{registration_key}'")


class STACWebHookEventRegistrationTable(
    NotificationRegistrationTableService[STACItemEventRegistration]
):
    _model = STACItemEventRegistration

    def _get_partition_key_from_registration(
        self,
        registration: STACItemEventRegistration,
        target_environment: Optional[str],
    ) -> str:
        target_environment = target_environment or DEFAULT_TARGET_ENVIRONMENT
        return f"{registration.collection_id}|||{target_environment}"

    def get_registration_key(
        self, notification: NotificationMessage, target_environment: Optional[str]
    ) -> Optional[str]:
        return super().get_registration_key(notification, target_environment)


class BlobTriggerEventRegistrationTable(
    CloudEventRegistrationTableService[BlobTriggerEventRegistration]
):
    _model = BlobTriggerEventRegistration

    def _get_partition_key_from_registration(
        self, registration: BlobTriggerEventRegistration
    ) -> str:
        return f"{registration.storage_account}||{registration.container}"

    def get_registration_key(self, event: CloudEvent) -> Optional[str]:
        if not event.subject:
            return None

        sa_match = re.match(STORAGE_ACCOUNT_REGEX, event.source)
        if not sa_match:
            return None
        else:
            storage_account = sa_match.group(1)
        cn_match = re.match(CONTAINER_REGEX, event.subject)
        if not cn_match:
            return None
        else:
            container = cn_match.group(1)

        return f"{storage_account}||{container}"
