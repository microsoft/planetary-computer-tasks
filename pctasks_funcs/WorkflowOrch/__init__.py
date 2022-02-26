import logging
from typing import Any, Dict, Generator, List, Optional, Union

import azure.durable_functions as df
from azure.durable_functions.models.Task import TaskBase
from func_lib.activities import call_activity
from func_lib.flows.update_record import UpdateRecordOrchFlow

from pctasks.core.logging import RunLogger
from pctasks.core.models.record import (
    JobRunRecord,
    JobRunStatus,
    WorkflowRunRecord,
    WorkflowRunStatus,
)
from pctasks.core.models.workflow import WorkflowSubmitMessage
from pctasks.core.utils import map_opt
from pctasks.execute.constants import (
    TASKS_TEMPLATE_PATH,
    ActivityNames,
    OrchestratorNames,
)
from pctasks.execute.dag import sort_jobs
from pctasks.execute.errors import WorkflowFailedError
from pctasks.execute.models import (
    CreateJobRunRecordUpdate,
    CreateWorkflowRunRecordUpdate,
    JobResultMessage,
    JobSubmitMessage,
    UpdateRecordMessage,
    WorkflowRunRecordUpdate,
)
from pctasks.execute.template import template_foreach, template_job_with_item

logger = logging.getLogger(__name__)


def orchestrator(context: df.DurableOrchestrationContext) -> Generator[Any, Any, Any]:
    msg = context.get_input()
    submit_message = WorkflowSubmitMessage.parse_obj(msg)
    run_record_id = submit_message.get_run_record_id()
    event_logger = RunLogger(run_record_id, logger_id=OrchestratorNames.WORKFLOW)

    workflow = submit_message.workflow
    trigger_event = map_opt(lambda e: e.dict(), submit_message.trigger_event)

    is_errored = False
    errors: Optional[List[str]] = None

    update_record_flow = UpdateRecordOrchFlow(
        context,
        event_logger,
        run_record_id=run_record_id,
    )

    ##################
    # Create records #
    ##################

    workflow_run_record = WorkflowRunRecord(
        dataset=submit_message.workflow.get_dataset_id(),
        run_id=submit_message.run_id,
        workflow=submit_message.workflow,
        trigger_event=submit_message.trigger_event,
        args=submit_message.args,
        status=WorkflowRunStatus.RECEIVED,
    )

    # Create the workflow run record.
    try:
        result = yield update_record_flow.create_task(
            update=CreateWorkflowRunRecordUpdate(
                record=workflow_run_record,
            ),
        )
        create_record_result = update_record_flow.handle_result(result)
        is_errored = is_errored or bool(create_record_result.error)
    except Exception as e:
        update_record_flow.handle_error(e)
        logger.exception(e)
        raise WorkflowFailedError(
            f"Failure creating records for workflow run {run_record_id}"
        )

    ####################
    # Begin processing #
    ####################

    try:
        # Template workflow with any arguments
        templated_workflow = submit_message.get_workflow_with_templated_args()
    except Exception as e:
        try:
            result = yield update_record_flow.create_task(
                update=WorkflowRunRecordUpdate(
                    dataset=workflow.get_dataset_id(),
                    run_id=submit_message.run_id,
                    status=WorkflowRunStatus.FAILED,
                    errors=[f"Failed to template workflow with args: {e}"],
                ),
            )
            update_record_result = update_record_flow.handle_result(result)
            is_errored = is_errored or bool(update_record_result.error)
        except Exception as e:
            update_record_flow.handle_error(e)
            logger.exception(e)
            raise WorkflowFailedError(
                f"Failure creating records for workflow run {run_record_id}"
            )
        return

    # Update workflow to running.
    try:
        result = yield update_record_flow.create_task(
            update=WorkflowRunRecordUpdate(
                dataset=workflow.get_dataset_id(),
                run_id=submit_message.run_id,
                status=WorkflowRunStatus.RUNNING,
            ),
        )
        create_record_result = update_record_flow.handle_result(result)
        is_errored = is_errored or bool(create_record_result.error)
    except Exception as e:
        update_record_flow.handle_error(e)
        errors = (errors or []) + [str(e)]
        is_errored = True

    job_outputs: Dict[str, Union[Dict[str, Any], List[Dict[str, Any]]]] = {}

    workflow_jobs = list(templated_workflow.jobs.values())

    # For now, sort based on dependencies.
    # TODO: Parallel execution of jobs based on dependencies.
    sorted_jobs = sort_jobs(workflow_jobs)

    try:
        # Collect job submit messages.
        for base_job in sorted_jobs:

            if base_job.foreach:
                items = template_foreach(
                    base_job.foreach,
                    job_outputs=job_outputs,
                    trigger_event=trigger_event,
                )
                jobs = [
                    template_job_with_item(base_job, item, i)
                    for i, item in enumerate(items)
                ]
            else:
                jobs = [base_job]

            job_submit_messages: List[JobSubmitMessage] = []

            for prepared_job in jobs:
                job_submit_message = JobSubmitMessage(
                    job=prepared_job,
                    dataset=workflow.get_dataset_id(),
                    run_id=submit_message.run_id,
                    job_id=prepared_job.get_id(),
                    tokens=workflow.tokens,
                    target_environment=workflow.target_environment,
                    job_outputs=job_outputs,
                    trigger_event=trigger_event,
                )

                # Update job to pending.
                try:
                    result = yield update_record_flow.create_task(
                        update=CreateJobRunRecordUpdate(
                            record=JobRunRecord(
                                job_id=prepared_job.get_id(),
                                run_id=submit_message.run_id,
                                status=JobRunStatus.PENDING,
                            ),
                        )
                    )

                    create_record_result = update_record_flow.handle_result(result)
                    is_errored = is_errored or bool(create_record_result.error)
                except Exception as e:
                    update_record_flow.handle_error(e)
                    errors = (errors or []) + [f"Error updating job record: {e}"]
                    is_errored = True

                if is_errored:
                    break

                job_submit_messages.append(job_submit_message)

            # Submit each job
            job_submits: List[TaskBase] = []
            for job_submit_message in job_submit_messages:
                job_orch_instance_id = context.new_guid().hex

                job_submits.append(
                    context.call_sub_orchestrator(
                        OrchestratorNames.JOB,
                        input_=job_submit_message.json(),
                        instance_id=job_orch_instance_id,
                    )
                )

            # Wait for all jobs to complete.
            if job_submits:
                job_result_strs = yield context.task_all(job_submits)

                job_results = [JobResultMessage.parse_raw(s) for s in job_result_strs]
                for job_result in job_results:
                    if job_result.errors or job_result.task_outputs is None:
                        raise WorkflowFailedError(
                            f"Job {job_result.job_id} failed. See job for details."
                        )

                if len(job_results) == 1:
                    job_outputs[base_job.get_id()] = {
                        TASKS_TEMPLATE_PATH: job_results[0].task_outputs
                    }
                else:
                    this_job_outputs: List[Dict[str, Any]] = []
                    for job_result in job_results:
                        this_job_outputs.append(
                            {TASKS_TEMPLATE_PATH: job_result.task_outputs}
                        )
                    job_outputs[base_job.get_id()] = this_job_outputs

                # if not context.is_replaying:
                #     import json

                #     logger.warning(json.dumps(job_outputs, indent=2))
            else:
                # Mark the job as having no tasks.
                try:
                    result = yield update_record_flow.create_task(
                        update=CreateJobRunRecordUpdate(
                            record=JobRunRecord(
                                job_id=base_job.get_id(),
                                run_id=submit_message.run_id,
                                status=JobRunStatus.NOTASKS,
                            ),
                        )
                    )

                    create_record_result = update_record_flow.handle_result(result)
                    is_errored = is_errored or bool(create_record_result.error)
                except Exception as e:
                    update_record_flow.handle_error(e)
                    is_errored = True

    except Exception as e:
        logger.exception(e)
        event_logger.log_event(f"Workflow failed: {e}")
        errors = (errors or []) + [str(e)]
        is_errored = True

    if is_errored:
        yield call_activity(
            context,
            name=ActivityNames.UPDATE_RECORD,
            msg=UpdateRecordMessage(
                update=WorkflowRunRecordUpdate(
                    dataset=workflow.get_dataset_id(),
                    run_id=submit_message.run_id,
                    status=WorkflowRunStatus.FAILED,
                    errors=errors,
                ),
            ),
            run_record_id=run_record_id,
        )
    else:
        yield call_activity(
            context,
            name=ActivityNames.UPDATE_RECORD,
            msg=UpdateRecordMessage(
                update=WorkflowRunRecordUpdate(
                    dataset=workflow.get_dataset_id(),
                    run_id=submit_message.run_id,
                    status=WorkflowRunStatus.COMPLETED,
                ),
            ),
            run_record_id=run_record_id,
        )

    if not context.is_replaying:
        event_logger.info("Workflow complete.")


main = df.Orchestrator.create(orchestrator)
