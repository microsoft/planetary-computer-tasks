# from typing import Optional

# import click
# from strictyaml.exceptions import MarkedYAMLError

# from pctasks.cli.cli import PCTasksCommandContext, cli_output, cli_print
# from pctasks.core.models.workflow import WorkflowSubmitMessage
# from pctasks.core.yaml import YamlValidationError
# from pctasks.dataset.constants import DEFAULT_DATASET_YAML_PATH
# from pctasks.dataset.template import template_dataset_file
# from pctasks.dataset.utils import opt_collection, opt_ds_config, opt_submit
# from pctasks.dataset.workflow import ProcessItemsWorkflowConfig
# from pctasks.submit.client import SubmitClient
# from pctasks.submit.settings import SubmitSettings


# @click.command("process-items")
# @click.argument("chunkset_id")
# @opt_ds_config
# @opt_collection
# @click.option(
#     "-t",
#     "--target",
#     help="The target environment to process the items in.",
# )
# @click.option("--limit", type=int, help="Limit, used for testing")
# @opt_submit
# @click.pass_context
# def process_items_cmd(
#     ctx: click.Context,
#     chunkset_id: str,
#     dataset: Optional[str],
#     collection: Optional[str],
#     target: str,
#     limit: Optional[int] = None,
#     submit: bool = False,
# ) -> None:
#     """Create and ingest items.

#     Read the asset paths from the chunk file at CHUNK and
#     submit a workflow to process into items and ingest into
#     the database.
#     """
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

#     workflow = ProcessItemsWorkflowConfig.from_collection(
#         dataset=ds_config,
#         collection=collection_config,
#         chunkset_id=chunkset_id,
#         ingest=True,
#         create_chunks_options=None,
#         create_items_options=None,
#         ingest_options=None,
#         target=target,
#         tags=None,
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
