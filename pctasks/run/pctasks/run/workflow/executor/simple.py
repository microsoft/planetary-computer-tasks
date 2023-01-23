import logging
import os
from importlib.metadata import EntryPoint
from typing import Any, Dict, List, Optional, Union

from pctasks.core.importer import ensure_code, ensure_requirements
from pctasks.core.models.task import (
    CompletedTaskResult,
    FailedTaskResult,
    TaskDefinition,
    TaskResult,
    WaitTaskResult,
)
from pctasks.core.models.workflow import JobDefinition, WorkflowDefinition
from pctasks.core.storage import StorageFactory
from pctasks.core.utils import environment, map_opt
from pctasks.run.constants import TASKS_TEMPLATE_PATH
from pctasks.run.dag import sort_jobs
from pctasks.run.errors import TaskFailedError
from pctasks.run.secrets.local import LocalSecretsProvider
from pctasks.run.template import template_args, template_foreach, template_job_with_item
from pctasks.task.context import TaskContext
from pctasks.task.run import MissingEnvironmentError, TaskLoadError
from pctasks.task.settings import TaskSettings
from pctasks.task.task import Task

logger = logging.getLogger(__name__)


class SimpleWorkflowExecutor:
    """Executes a workflow by running all tasks locally and sequentially."""

    def run_task(
        self,
        task_config: TaskDefinition,
        context: TaskContext,
        output_uri: Optional[str] = None,
    ) -> TaskResult:
        """Runs a task in a local setting, without communicating with a task runner.

        Useful for running tasks locally without going through the submit process.
        """
        logger.info(" === PCTasks (simple workflow runner) ===")

        logger.debug(task_config.to_yaml())

        try:
            if task_config.code:
                task_settings = TaskSettings.get()
                if task_config.code.requirements:
                    (
                        req_storage,
                        req_path,
                    ) = context.storage_factory.get_storage_for_file(
                        task_config.code.requirements
                    )
                    ensure_requirements(
                        req_path,
                        req_storage,
                        task_config.code.pip_options,
                        task_settings.code_dir,
                    )

                code_storage, code_path = context.storage_factory.get_storage_for_file(
                    task_config.code.src
                )
                ensure_code(code_path, code_storage, target_dir=task_settings.code_dir)

            task_path = task_config.task

            entrypoint = EntryPoint("", task_path, "")
            try:
                task = entrypoint.load()
                if callable(task):
                    task = task()
            except Exception as e:
                raise TaskLoadError(f"Failed to load task: {task_path}") from e

            if not isinstance(task, Task):
                raise TaskLoadError(
                    f"{task_path} of type {type(task)} {task} "
                    f"is not an instance of {Task}"
                )

            # Substitute local secrets and set environment variables.
            env = task_config.environment or {}
            if env:
                env = LocalSecretsProvider(settings=None).substitute_secrets(env)

            with environment(**env):
                missing_env: List[str] = []
                for env_var in task.get_required_environment_variables():
                    if env_var not in os.environ:
                        missing_env.append(env_var)
                if missing_env:
                    missing_env_str = ", ".join(f'"{e}"' for e in missing_env)
                    raise MissingEnvironmentError(
                        "The task cannot run due to the following "
                        f"missing environment variables: {missing_env_str}"
                    )
                logger.info("  -- PCTasks: Running task...")
                result = task.parse_and_run(task_config.args, context)

                logger.info("  -- PCTasks: Handling task result...")

            # Save output
            if output_uri:
                storage, path = context.storage_factory.get_storage_for_file(output_uri)
                storage.write_text(path, result.json(indent=2))

            logger.info(" === PCTasks: Task completed! ===")

            return result

        except Exception as e:
            logger.info(" === PCTasks: Task Failed! ===")
            logger.exception(e)
            raise

    def run_job(
        self,
        job: JobDefinition,
        context: TaskContext,
        previous_job_outputs: Optional[Dict[str, Any]] = None,
        output_uri: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Runs a job and returns the final task result."""
        task_outputs: Dict[str, Any] = {}

        for task_config in job.tasks:
            copied_task = task_config.__class__.parse_obj(task_config.dict())
            copied_task.args = template_args(
                copied_task.args,
                job_outputs=previous_job_outputs or {},
                task_outputs=task_outputs,
                trigger_event=None,
            )
            task_result = self.run_task(
                copied_task,
                context,
                output_uri=map_opt(
                    lambda p: os.path.join(p, copied_task.id), output_uri
                ),
            )

            if isinstance(task_result, CompletedTaskResult):
                task_outputs[task_config.id] = {"output": task_result.output}
            elif isinstance(task_result, FailedTaskResult):
                raise TaskFailedError(
                    f"Task failed: {','.join(task_result.errors or ['Task errored.'])}"
                )
            elif isinstance(task_result, WaitTaskResult):
                raise TaskFailedError(
                    f"Task responded with WaitTaskResult: {task_result.message}"
                )
            else:
                raise TaskFailedError(f"Unknown task result: {task_result}")

        return task_outputs

    def run_workflow(
        self,
        workflow: WorkflowDefinition,
        context: Optional[TaskContext] = None,
        output_uri: Optional[str] = None,
        args: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Runs a workflow and returns the final task result."""
        # Keep in sync with the Azure Functions execution workflow.

        job_outputs: Dict[str, Union[Dict[str, Any], List[Dict[str, Any]]]] = {}

        errors = workflow.get_argument_errors(args)
        if errors:
            raise ValueError(f"Argument errors: {';'.join(errors)}")

        if args:
            workflow = workflow.template_args(args)
        else:
            if workflow.args:
                pass

        if not context:
            context = TaskContext(
                storage_factory=StorageFactory(), run_id=workflow.name
            )

        workflow_jobs = list(workflow.jobs.values())
        sorted_jobs = sort_jobs(workflow_jobs)
        for base_job in sorted_jobs:

            if base_job.foreach:
                items = template_foreach(
                    base_job.foreach,
                    job_outputs=job_outputs,
                    trigger_event=None,
                )
                jobs = [
                    template_job_with_item(base_job, item)
                    for i, item in enumerate(items)
                ]
            else:
                jobs = [base_job]

            job_results: List[Dict[str, Any]] = []
            for prepared_job in jobs:
                job_result = self.run_job(
                    prepared_job,
                    context,
                    job_outputs,
                    output_uri=map_opt(
                        lambda p: os.path.join(p, prepared_job.get_id()), output_uri
                    ),
                )

                job_results.append(job_result)

            if len(job_results) == 1:
                job_outputs[base_job.get_id()] = {TASKS_TEMPLATE_PATH: job_results[0]}
            else:
                job_output_entry: List[Dict[str, Any]] = []
                for job_result in job_results:
                    job_output_entry.append({TASKS_TEMPLATE_PATH: job_result})
                job_outputs[base_job.get_id()] = job_output_entry

        return job_outputs
