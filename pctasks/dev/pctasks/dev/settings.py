from pathlib import Path
from typing import Union

from pctasks.core.settings import PCTasksSettings

HERE = Path(__file__).parent
DEFAULT_COSMOSDB_SCRIPTS_PATH = (
    HERE / ".." / ".." / ".." / ".." / "deployment/cosmosdb/scripts"
)
COSMOSDB_STORED_PROCS_DIR = "stored_procs"
COSMOSDB_TRIGGERS_DIR = "triggers"
COSMOSDB_UDFS_DIR = "udfs"


class DevSettings(PCTasksSettings):
    @classmethod
    def section_name(cls) -> str:
        return "dev"

    cosmosdb_emulator_scripts_dir: Union[str, Path] = DEFAULT_COSMOSDB_SCRIPTS_PATH
    """Directory containing scripts for Cosmos DB.

    This includes stored procedures triggers, and udfs.

    Defaults to the correct location in the pctasks repository.
    """

    def get_cosmosdb_emulator_stored_procs_dir(self) -> Path:
        return (
            Path(self.cosmosdb_emulator_scripts_dir) / COSMOSDB_STORED_PROCS_DIR
        ).resolve()

    def get_cosmosdb_emulator_triggers_dir(self) -> Path:
        return (
            Path(self.cosmosdb_emulator_scripts_dir) / COSMOSDB_TRIGGERS_DIR
        ).resolve()

    def get_cosmosdb_emulator_udfs_dir(self) -> Path:
        return (Path(self.cosmosdb_emulator_scripts_dir) / COSMOSDB_UDFS_DIR).resolve()
