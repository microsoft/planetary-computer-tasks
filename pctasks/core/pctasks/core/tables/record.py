# import logging
# from abc import ABC, abstractmethod
# from typing import Generic, List, Optional, Tuple, TypeVar

# from pctasks.core.models.base import RunRecordId
# from pctasks.core.models.run import (
#     JobRunRecord,
#     RunRecord,
#     TaskRunRecord,
#     WorkflowRunRecord,
# )
# from pctasks.core.models.utils import tzutc_now
# from pctasks.core.tables.base import ModelTableService

# R = TypeVar("R", bound=RunRecord)

# logger = logging.getLogger(__name__)


# class RunRecordTable(ABC, Generic[R], ModelTableService[R]):
#     @abstractmethod
#     def _get_key_from_record(self, record: R) -> Tuple[str, str]:
#         ...

#     @abstractmethod
#     def _get_key_from_run_id(self, run_record_id: RunRecordId) -> Tuple[str, str]:
#         ...

#     def insert_record(self, record: R) -> None:
#         key = self._get_key_from_record(record)
#         self.insert(
#             partition_key=key[0],
#             row_key=key[1],
#             entity=record,
#         )

#     def upsert_record(self, record: R) -> None:
#         record.updated = tzutc_now()
#         key = self._get_key_from_record(record)
#         self.upsert(
#             partition_key=key[0],
#             row_key=key[1],
#             entity=record,
#         )

#     def update_record(self, record: R) -> None:
#         record.updated = tzutc_now()
#         key = self._get_key_from_record(record)
#         self.update(
#             partition_key=key[0],
#             row_key=key[1],
#             entity=record,
#         )

#     def get_record(self, run_record_id: RunRecordId) -> Optional[R]:
#         key = self._get_key_from_run_id(run_record_id)
#         return self.get(
#             partition_key=key[0],
#             row_key=key[1],
#         )

#     def get_records(self) -> List[R]:
#         return self.fetch_all()


# class TaskRunRecordTable(RunRecordTable[TaskRunRecord]):
#     _model = TaskRunRecord

#     def get_run_record_id(self, run_id: str, job_id: str, task_id: str
# ) -> RunRecordId:
#         return RunRecordId(run_id=run_id, job_id=job_id, task_id=task_id)

#     def _get_key_from_record(self, record: TaskRunRecord) -> Tuple[str, str]:
#         return (record.run_id, f"{record.job_id}||{record.task_id}")

#     def _get_key_from_run_id(self, run_record_id: RunRecordId) -> Tuple[str, str]:
#         if not run_record_id.job_id:
#             raise ValueError(f"run_id.job_id is required: {run_record_id}")
#         if not run_record_id.task_id:
#             raise ValueError(f"run_id.task_id is required: {run_record_id}")

#         return (
#             run_record_id.run_id,
#             f"{run_record_id.job_id}||{run_record_id.task_id}",
#         )

#     def get_tasks(self, run_id: str, job_id: str) -> List[TaskRunRecord]:
#         return [
#             task
#             for task in self.query(
#                 f"PartitionKey eq '{run_id}'",
#             )
#             if task.job_id == job_id
#         ]


# class JobRunRecordTable(RunRecordTable[JobRunRecord]):
#     _model = JobRunRecord

#     def get_run_record_id(self, run_id: str, job_id: str) -> RunRecordId:
#         return RunRecordId(run_id=run_id, job_id=job_id)

#     def _get_key_from_record(self, record: JobRunRecord) -> Tuple[str, str]:
#         return (record.run_id, record.job_id)

#     def _get_key_from_run_id(self, run_record_id: RunRecordId) -> Tuple[str, str]:
#         if not run_record_id.job_id:
#             raise ValueError(f"run_id.job_id is required: {run_record_id}")

#         return (run_record_id.run_id, run_record_id.job_id)

#     def get_jobs(self, run_id: str) -> List[JobRunRecord]:
#         return self.query(
#             f"PartitionKey eq '{run_id}'",
#         )


# class WorkflowRunRecordTable(RunRecordTable[WorkflowRunRecord]):
#     _model = WorkflowRunRecord

#     def get_run_record_id(self, dataset: DatasetIdentifier, run_id: str
# ) -> RunRecordId:
#         return RunRecordId(dataset_id=str(dataset), run_id=run_id)

#     def _get_key_from_record(self, record: WorkflowRunRecord) -> Tuple[str, str]:
#         return (record.dataset_id, record.run_id)

#     def _get_key_from_run_id(self, run_record_id: RunRecordId) -> Tuple[str, str]:
#         if not run_record_id.dataset_id:
#             raise ValueError(f"run_id.dataset_id is required: {run_record_id}")
#         return (
#             DatasetIdentifier.from_string(run_record_id.dataset_id).as_key(),
#             run_record_id.run_id,
#         )

#     def get_workflow_runs(self, dataset: str) -> List[WorkflowRunRecord]:
#         partition_key = dataset.as_key()
#         return self.query(
#             f"PartitionKey eq '{partition_key}'",
#         )

#     def get_workflow_run(
#         self, run_id: str, dataset: Optional[DatasetIdentifier] = None
#     ) -> Optional[WorkflowRunRecord]:
#         """Returns the workflow run record for the given run_id.

#         If dataset is provided, queries with a partiion key. If not,
#         the first instance of a row key with the run_id is returned.
#         """
#         if dataset:
#             return self.get_record(
#                 self.get_run_record_id(dataset=dataset, run_id=run_id),
#             )
#         else:
#             return next(
#                 iter(
#                     self.query(
#                         f"RowKey eq '{run_id}'",
#                     )
#                 ),
#                 None,
#             )
