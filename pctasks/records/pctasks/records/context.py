from dataclasses import dataclass

from pctasks.cli.cli import PCTasksCommandContext


@dataclass
class RecordsCommandContext(PCTasksCommandContext):
    pretty_print: bool = False
    """Whether to pretty print the output, e.g. syntax highlight YAML."""
