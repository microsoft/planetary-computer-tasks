import logging

from pctasks.core.models.record import (
    JobRunRecord,
    RunRecord,
    TaskRunRecord,
    WorkflowRunGroupRecord,
    WorkflowRunRecord,
)
from pctasks.core.utils.backoff import with_backoff
from pctasks.run.models import (
    JobRunRecordUpdate,
    RecordUpdate,
    TaskRunRecordUpdate,
    WorkflowRunGroupRecordUpdate,
    WorkflowRunRecordUpdate,
)
from pctasks.run.settings import RunSettings

logger = logging.getLogger(__name__)


class RecordUpdateError(Exception):
    pass


class RecordUpdater:
    def __init__(self, settings: RunSettings):
        self.settings = settings

    def upsert_record(self, record: RunRecord) -> None:
        def _do_upsert() -> None:
            # Workflow Group
            if isinstance(record, WorkflowRunGroupRecord):
                with self.settings.get_workflow_run_group_record_table() as wrg_table:
                    wrg_table.upsert_record(record)

            # Workflow
            if isinstance(record, WorkflowRunRecord):
                with self.settings.get_workflow_run_record_table() as wr_table:
                    wr_table.upsert_record(record)

            # Workflow Run Group
            if isinstance(record, JobRunRecord):
                with self.settings.get_job_run_record_table() as jr_table:
                    jr_table.upsert_record(record)

            # Workflow Run Group
            if isinstance(record, TaskRunRecord):
                with self.settings.get_task_run_record_table() as tr_table:
                    tr_table.upsert_record(record)

        with_backoff(_do_upsert)

    def update_record(self, update: RecordUpdate) -> None:
        def _do_update() -> None:
            # Workflow  Group
            if isinstance(update, WorkflowRunGroupRecordUpdate):
                logger.debug(
                    f"Updating workflow run group record status to {update.status}."
                )
                with self.settings.get_workflow_run_group_record_table() as wrg_table:
                    wrg_record = wrg_table.get_record(
                        dataset=update.dataset, group_id=update.group_id
                    )
                    if not wrg_record:
                        raise RecordUpdateError(
                            "Workflow group record for "
                            f"{update.dataset}/{update.group_id} "
                            "expected but not found.",
                        )
                    wrg_record.set_update_time()
                    update.update_record(wrg_record)
                    wrg_table.update_record(wrg_record)

            # Workflow
            elif isinstance(update, WorkflowRunRecordUpdate):
                logger.debug(f"Updating workflow run record status to {update.status}.")
                with self.settings.get_workflow_run_record_table() as wr_table:
                    wr_record = wr_table.get_record(update.get_run_record_id())
                    if not wr_record:
                        raise RecordUpdateError(
                            "Workflow record for "
                            f"{update.get_run_record_id()} "
                            "expected but not found.",
                        )
                    wr_record.set_update_time()
                    update.update_record(wr_record)
                    wr_table.update_record(wr_record)

            # Job
            elif isinstance(update, JobRunRecordUpdate):
                logger.debug(f"Updating job run record status to {update.status}.")
                with self.settings.get_job_run_record_table() as jr_table:
                    jr_record = jr_table.get_record(update.get_run_record_id())
                    if not jr_record:
                        raise RecordUpdateError(
                            "Job record for "
                            f"{update.get_run_record_id()} "
                            "expected but not found.",
                        )
                    jr_record.set_update_time()
                    update.update_record(jr_record)
                    jr_table.update_record(jr_record)

            # Task

            elif isinstance(update, TaskRunRecordUpdate):
                with self.settings.get_task_run_record_table() as tr_table:
                    logger.debug(f"Updating task run record status to {update.status}.")
                    tr_record = tr_table.get_record(update.get_run_record_id())
                    if not tr_record:
                        raise RecordUpdateError(
                            "Task record for "
                            f"{update.get_run_record_id()} "
                            "expected but not found.",
                        )
                    tr_record.set_update_time()
                    update.update_record(tr_record)
                    tr_table.update_record(tr_record)

            else:
                raise RecordUpdateError(
                    f"Unexpected record update type: {type(update)}"
                )

        with_backoff(_do_update)
