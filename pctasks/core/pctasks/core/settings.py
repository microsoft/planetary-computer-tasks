import logging
import os
from abc import abstractmethod
from pathlib import Path
from typing import (
    Any,
    Dict,
    Hashable,
    List,
    Optional,
    OrderedDict,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
)

import strictyaml
from cachetools import Cache, LRUCache, cachedmethod
from cachetools.keys import hashkey
from pydantic import BaseSettings, Field, ValidationError
from pydantic.env_settings import SettingsSourceCallable

from pctasks.core.constants import (
    DEFAULT_PROFILE,
    ENV_VAR_PCTASK_PREFIX,
    ENV_VAR_PCTASKS_PROFILE,
    SETTINGS_DIR_ENV_VAR,
    SETTINGS_ENV_DIR,
)
from pctasks.core.context import PCTasksCommandContext
from pctasks.core.models.base import PCBaseModel
from pctasks.core.utils import map_opt

T = TypeVar("T", bound="PCTasksSettings")

logger = logging.getLogger(__name__)


def get_settings_dir() -> Path:
    return Path(os.environ.get(SETTINGS_DIR_ENV_VAR, SETTINGS_ENV_DIR)).expanduser()


class SettingsLoadError(Exception):
    pass


class SettingsError(Exception):
    def __init__(
        self,
        message: str,
        path: Optional[str] = None,
        validation_error: Optional[ValidationError] = None,
        *args: object,
    ) -> None:
        self.message = message
        self.path = path
        self.validation_error = validation_error
        super().__init__(message, *args)


class SettingsConfig(PCBaseModel):
    _cache: Cache = LRUCache(maxsize=100)

    """Configuration for the settings location."""
    profile: Optional[str] = None
    settings_file: Optional[str] = None

    @classmethod
    @cachedmethod(lambda cls: cls._cache)
    def get(
        cls,
        profile: Optional[str] = None,
        settings_file: Optional[Union[str, Path]] = None,
    ) -> "SettingsConfig":
        settings_file = map_opt(lambda x: Path(x), settings_file)
        settings_dir = get_settings_dir()
        config_file = settings_dir / ".config.yaml"
        config: Optional[SettingsConfig] = None
        if config_file.exists():
            try:
                config = SettingsConfig.from_yaml(config_file.read_text())
            except Exception as e:
                logger.warning(
                    f"Failed to load settings config from {config_file}: {e}"
                )

        if not config:
            config = SettingsConfig()

        # Replace profile with the environment variable if it is set
        if ENV_VAR_PCTASKS_PROFILE in os.environ:
            config.profile = os.environ[ENV_VAR_PCTASKS_PROFILE]

        # Use explicit values if present
        if profile:
            config.profile = profile
        if settings_file:
            config.settings_file = str(settings_file)

        # Use the default profile if none is provided
        if not config.profile:
            config.profile = DEFAULT_PROFILE

        return config

    def write(self) -> None:
        settings_dir = get_settings_dir()
        try:
            settings_dir.mkdir(exist_ok=True)
        except Exception:
            # Don't fail if we can't create the settings directory
            logger.warning(f"Could not create settings directory {settings_dir}")
            return
        config_file = settings_dir / ".config.yaml"
        config_file.write_text(self.to_yaml())

    def get_settings_file(self) -> Path:
        settings_dir = get_settings_dir()
        _settings_file: Optional[str]
        if self.settings_file:
            _settings_file = self.settings_file
        else:
            _settings_file = map_opt(
                str, next(settings_dir.glob(f"{self.profile}.y*ml"), None)
            )
            if not _settings_file:
                _settings_file = str(settings_dir / f"{self.profile}.yaml")

        return Path(_settings_file)

    @classmethod
    def get_profile_names(cls) -> List[str]:
        settings_dir = get_settings_dir()
        if not settings_dir.exists():
            return []
        return [
            f.stem for f in settings_dir.glob("*.y*ml") if not f.name.startswith(".")
        ]

    @property
    def is_profile_from_environment(self) -> bool:
        return (
            ENV_VAR_PCTASKS_PROFILE in os.environ
            and self.profile == os.environ[ENV_VAR_PCTASKS_PROFILE]
        )


def _get_yaml_settings_source(
    settings_file: Path,
) -> SettingsSourceCallable:
    def yaml_config_settings_source(settings: BaseSettings) -> Dict[str, Any]:
        """
        A settings source that loads configuration from YAML.
        """
        if settings_file.exists():
            with open(settings_file) as f:
                yaml_txt = f.read()
            yml: strictyaml.YAML = strictyaml.load(yaml_txt)
            return cast(OrderedDict[str, Any], yml.data)
        else:
            return {}

    return yaml_config_settings_source


def get_settings(
    model: Type[T],
    section_name: str,
    profile: Optional[str] = None,
    settings_file: Optional[Path] = None,
) -> T:
    settings_config = SettingsConfig.get(profile=profile, settings_file=settings_file)
    _settings_file = settings_config.get_settings_file()

    class _Settings(BaseSettings):
        # mypy doesn't like using type vars here,
        # but it works and defines pydantic validation.
        section: model = Field(  # type: ignore
            default_factory=model,
            alias=section_name,
            env=f"{ENV_VAR_PCTASK_PREFIX}{section_name.upper()}",
        )

        class Config:
            env_prefix = ENV_VAR_PCTASK_PREFIX
            extra = "ignore"
            env_nested_delimiter = "__"

            @classmethod
            def customise_sources(
                cls,
                init_settings: SettingsSourceCallable,
                env_settings: SettingsSourceCallable,
                file_secret_settings: SettingsSourceCallable,
            ) -> Any:
                if _settings_file.exists():
                    return (
                        init_settings,
                        env_settings,
                        _get_yaml_settings_source(_settings_file),
                        file_secret_settings,
                    )
                else:
                    return (
                        init_settings,
                        env_settings,
                        file_secret_settings,
                    )

    try:
        # type ignore as pydantic reports issue with missing 'section'
        # but this is supplied by the settings mechanism.
        settings = _Settings()  # type:ignore
        return settings.section
    except Exception as e:
        msg = "Could not load settings from environment"
        if _settings_file:
            msg += f" or settings file at {_settings_file}"
        msg += f" - {e}"
        raise SettingsError(
            msg,
            path=str(_settings_file),
            validation_error=e if isinstance(e, ValidationError) else None,
        ) from e


def settings_hash_key(
    cls: Type[T],
    profile: Optional[str] = None,
    settings_file: Optional[str] = None,
) -> Tuple[Hashable, ...]:
    return hashkey((cls.section_name(), profile, settings_file))


class PCTasksSettings(PCBaseModel):
    _cache: Cache = LRUCache(maxsize=100)

    @classmethod
    @abstractmethod
    def section_name(cls) -> str:
        raise NotImplementedError

    @classmethod
    @cachedmethod(lambda cls: cls._cache, key=settings_hash_key)
    def get(
        cls: Type[T],
        profile: Optional[str] = None,
        settings_file: Optional[Union[str, Path]] = None,
    ) -> T:
        try:
            return get_settings(
                cls,
                cls.section_name(),
                profile=profile,
                settings_file=map_opt(lambda x: Path(x), settings_file),
            )
        except Exception as e:
            raise SettingsLoadError(f"Failed to load settings.: {e}") from e

    @classmethod
    def from_context(cls: Type[T], context: PCTasksCommandContext) -> T:
        return cls.get(context.profile, context.settings_file)
