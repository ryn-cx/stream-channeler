# TODO: Validate
"""What every part of a plugin is built on: who it is, and what it holds open."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, ClassVar

from sqlmodel import Session

from app.plugins.models import Plugin
from app.sources.models import Source
from plugins.utils.base_plugin_v2.files import INITIAL_FILE_IDENTIFIER, BaseFile

if TYPE_CHECKING:
    from plugins.utils.base_plugin_v2.importer import BaseImporter
    from plugins.utils.base_plugin_v2.initialize import BasePluginInitializer


# TODO: Validate
class BasePluginCore(ABC):
    """The session, the stored plugin, and the names the plugin goes by."""

    session: Session
    plugin: Plugin
    _sources: dict[str, Source]
    _file_cache: dict[object, Any]
    initializer: ClassVar[type[BasePluginInitializer]]
    importer: ClassVar[type[BaseImporter]]

    # TODO: Validate
    def __init__(self, session: Session) -> None:
        self.session = session
        self._file_cache = {}
        self.plugin = Plugin.get_one(session, self.plugin_name())
        self._sources = {source.key: source for source in self.plugin.sources}

    # TODO: Validate
    @classmethod
    @abstractmethod
    def plugin_name(cls) -> str: ...

    # TODO: Validate
    @classmethod
    @abstractmethod
    def favicon_url(cls) -> str | None: ...

    # TODO: Validate
    @classmethod
    def name_on_tmdb(cls) -> tuple[str, ...]:
        return (cls.plugin_name(),)

    # TODO: Validate
    @classmethod
    def _source_keys(cls) -> tuple[str, ...]:
        return (cls.plugin_name(),)

    # TODO: Validate
    @classmethod
    def matches_tmdb_provider(cls, provider_name: str) -> bool:
        return provider_name in cls.name_on_tmdb()

    # TODO: Validate
    def clear_file_cache(self) -> None:
        self._file_cache.clear()

    # TODO: Validate
    def _file[FileT: BaseFile[Any]](
        self,
        file_type: Callable[..., FileT],
        *identifiers: object,
    ) -> FileT:
        """Return the cached `file_type` instance for `identifiers`."""
        cache_key = (file_type, identifiers)
        cached: FileT | None = self._file_cache.get(cache_key)
        if cached is not None:
            return cached
        file = file_type(self.session, self.plugin, *identifiers)
        self._file_cache[cache_key] = file
        return file

    # TODO: Validate
    def _initial_file[FileT: BaseFile[Any]](
        self,
        file_type: Callable[..., FileT],
    ) -> FileT:
        """Return the `file_type` instance a timestamped series of files starts at."""
        return self._file(file_type, INITIAL_FILE_IDENTIFIER)
