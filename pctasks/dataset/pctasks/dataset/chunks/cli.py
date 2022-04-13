# import logging
# from typing import Optional

# import click
# from pctasks.core.models.base import ForeachConfig
# from pctasks.dataset.splits.models import CreateSplitsOptions, CreateSplitsTaskConfig
# from pystac.utils import str_to_datetime
# from strictyaml.exceptions import MarkedYAMLError

# from pctasks.cli.cli import PCTasksCommandContext, cli_output, cli_print
# from pctasks.core.models.workflow import (
#     JobConfig,
#     WorkflowConfig,
#     WorkflowSubmitMessage,
# )
# from pctasks.core.utils import map_opt
# from pctasks.core.yaml import YamlValidationError
# from pctasks.dataset.chunks.constants import ALL_CHUNK_PREFIX, ASSET_CHUNKS_PREFIX
# from pctasks.dataset.chunks.models import ChunksOptions, CreateChunksTaskConfig
# from pctasks.dataset.chunks.task import CreateChunksInput
# from pctasks.dataset.constants import DEFAULT_DATASET_YAML_PATH
# from pctasks.dataset.template import template_dataset_file
# from pctasks.dataset.utils import opt_collection, opt_ds_config, opt_submit
# from pctasks.submit.client import SubmitClient
# from pctasks.submit.settings import SubmitSettings

# logger = logging.getLogger(__name__)


# @click.command("create-chunks")
# @click.argument("chunkset_id")
# @click.argument("assets_uri")
# @opt_ds_config
# @opt_collection
# @click.option(
#     "-s",
#     "--since",
#     help=("Only process files that have been modified at or after this datetime."),
# )
# @click.option("--local", is_flag=True, help="Run locally, do not submit as a task")
# @click.option("--limit", type=int, help="Limit prefix linking, used for testing")
# @opt_submit
# @click.pass_context
# def create_chunks_cmd(
#     ctx: click.Context,
#     chunkset_id: str,
#     assets_uri: str,
#     dataset: Optional[str] = None,
#     collection: Optional[str] = None,
#     prefix: Optional[str] = None,
#     since: Optional[str] = None,
#     limit: Optional[int] = None,
#     submit: bool = False,
# ) -> None:
#     """Creates asset chunks for bulk processing."""
#     context: PCTasksCommandContext = ctx.obj
#     try:
#         ds_config = template_dataset_file(dataset)
#     except (MarkedYAMLError, YamlValidationError) as e:
#         raise click.ClickException(f"Invalid dataset config.\n{e}")
#     except FileNotFoundError:
#         raise click.ClickException(
#             "No dataset config found. Use --config to specify "
#             f"or name your config {DEFAULT_DATASET_YAML_PATH}."
#         )

#     if not ds_config:
#         raise click.ClickException("No dataset config found.")

#     collection_config = ds_config.get_collection(collection)
#     chunk_storage_config = collection_config.chunk_storage

#     splits_task_config = CreateSplitsTaskConfig.from_collection(
#         ds_config, collection_config, options=CreateSplitsOptions(limit=limit)
#     )

#     splits_job_config = JobConfig(id="create-splits", tasks=[splits_task_config])

#     chunk_folder = f"{chunkset_id}/{ASSET_CHUNKS_PREFIX}/{ALL_CHUNK_PREFIX}"

#     chunks_task_config = CreateChunksTaskConfig.create(
#         image=ds_config.image,
#         args=CreateChunksInput(
#             src_storage_uri="${{ item.uri }}",
#             dst_storage_uri=chunk_storage_config.get_uri(chunk_folder),
#             options=ChunksOptions(
#                 chunk_length="${{ item.chunk_length }}",
#                 since=map_opt(str_to_datetime, since),
#             ),
#         ),
#     )

#     chunks_job_config = JobConfig(
#         id="create-chunks",
#         tasks=[chunks_task_config],
#         foreach=ForeachConfig(
#             items="${{ "
#             + f"jobs.{splits_job_config.id}.tasks.{splits_task_config.id}.output"
#             + " }}"
#         ),
#     )

#     workflow = WorkflowConfig(
#         name=f"Create chunks for {collection_config.id}",
#         dataset=ds_config.get_identifier(),
#         collection_id=collection_config.id,
#         image=ds_config.image,
#         tokens=collection_config.get_tokens(),
#         jobs={
#             splits_job_config.id: splits_job_config,
#             chunks_job_config.id: chunks_job_config,
#         },
#     )

#     submit_message = WorkflowSubmitMessage(workflow=workflow)

#     if not submit:
#         cli_output(submit_message.to_yaml())
#     else:
#         settings = SubmitSettings.get(context.profile, context.settings_file)
#         with SubmitClient(settings) as client:
#             cli_print(
#                 click.style(f"  Submitting {submit_message.run_id}...", fg="green")
#             )
#             client.submit_workflow(submit_message)
