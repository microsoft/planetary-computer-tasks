import os
from abc import abstractmethod
from pathlib import Path
from typing import (
    Any,
    Dict,
    Hashable,
    Optional,
    OrderedDict,
    Tuple,
    Type,
    TypeVar,
    cast,
)

import strictyaml
from cachetools import Cache, LRUCache, cachedmethod
from cachetools.keys import hashkey
from pydantic import BaseSettings, Field, ValidationError
from pydantic.env_settings import SettingsSourceCallable

from pctasks.core.cli import PCTasksCommandContext
from pctasks.core.constants import (
    DEFAULT_PROFILE,
    ENV_VAR_PCTASK_PREFIX,
    ENV_VAR_PCTASKS_PROFILE,
    SETTINGS_ENV_DIR,
)
from pctasks.core.logging import RunLogger
from pctasks.core.models.base import PCBaseModel
from pctasks.core.utils import map_opt

T = TypeVar("T", bound="PCTasksSettings")


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


def _get_yaml_settings_source(
    settings_file: str,
) -> SettingsSourceCallable:
    def yaml_config_settings_source(settings: BaseSettings) -> Dict[str, Any]:
        """
        A settings source that loads configuration from YAML.
        """
        if Path(settings_file).exists():
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
    settings_file: Optional[str] = None,
) -> T:
    profile = profile or os.getenv(ENV_VAR_PCTASKS_PROFILE) or DEFAULT_PROFILE
    settings_dir = Path(SETTINGS_ENV_DIR).expanduser()
    settings_dir.mkdir(exist_ok=True)

    _settings_file: Optional[str]
    if settings_file:
        _settings_file = settings_file
    else:
        _settings_file = map_opt(str, next(settings_dir.glob(f"{profile}.y*ml"), None))
        if not _settings_file:
            _settings_file = str(settings_dir / f"{profile}.yaml")

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
                if _settings_file and Path(_settings_file).exists():
                    return (
                        init_settings,
                        env_settings,
                        _get_yaml_settings_source(str(_settings_file)),
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
            path=_settings_file,
            validation_error=e if isinstance(e, ValidationError) else None,
        ) from e


def settings_hash_key(
    cls: Type[T],
    profile: Optional[str] = None,
    settings_file: Optional[str] = None,
    event_logger: Optional[RunLogger] = None,
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
        settings_file: Optional[str] = None,
        event_logger: Optional[RunLogger] = None,
    ) -> T:
        try:
            return get_settings(
                cls,
                cls.section_name(),
                profile=profile,
                settings_file=settings_file,
            )
        except Exception as e:
            raise SettingsLoadError(f"Failed to load settings.: {e}") from e

    @classmethod
    def from_context(cls: Type[T], context: PCTasksCommandContext) -> T:
        return cls.get(context.profile, context.settings_file)
