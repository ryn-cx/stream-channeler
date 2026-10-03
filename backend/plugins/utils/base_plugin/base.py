from __future__ import annotations

import inspect
import re
from abc import ABC, abstractmethod
from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING, override

from plugins.utils.abstract_plugin import AbstractPlugin
from plugins.utils.base_plugin.core import BasePluginCore

if TYPE_CHECKING:
    from datetime import datetime

    from sqlmodel import Session

    from app.channels.models import Channel
    from app.files.models import File
    from app.plugins.models import Plugin
    from app.sources.models import Source
    from app.titles.models import Title
    from plugins.utils.abstract_plugin import TMDBLookupInfo
    from plugins.utils.base_plugin.linker import BasePluginLinker
    from plugins.utils.base_plugin.updater import BasePluginUpdater


# TODO: Validate
class BasePlugin(BasePluginCore, AbstractPlugin, ABC):
    # TODO: Validate
    @classmethod
    @abstractmethod
    def _plugin_updater_class(cls) -> type[BasePluginUpdater]: ...

    # TODO: Validate
    def _plugin_updater(self) -> BasePluginUpdater:
        return self._plugin_updater_class()(self.session, self.plugin, self._file_cache)

    # TODO: Validate
    @classmethod
    @abstractmethod
    def _plugin_linker_class(cls) -> type[BasePluginLinker]: ...

    # TODO: Validate
    def _plugin_linker(self) -> BasePluginLinker:
        return self._plugin_linker_class()(self.session, self.plugin, self._file_cache)

    # TODO: Validate
    @classmethod
    @override
    def initialize_plugin(cls, session: Session) -> None:
        cls._plugin_updater_class().initialize_plugin(session)

    # TODO: Validate
    @classmethod
    @override
    def matches_tmdb_provider(cls, provider_name: str) -> bool:
        return cls._plugin_linker_class().matches_tmdb_provider(provider_name)

    # TODO: Validate
    @classmethod
    @override
    def is_valid_url_format(cls, url: str) -> bool:
        """Return whether the given URL matches the plugin's URL format."""
        # is not None is used to booleanize the response.
        return bool(cls._url_regexes()) and re.match(cls._url_regex(), url) is not None

    # TODO: Validate
    @classmethod
    @override
    def url_domains(cls) -> list[str]:
        return cls._domains()

    # TODO: Validate
    @override
    def create_initial_channel_records(self) -> None:
        self._plugin_updater().create_initial_channel_records()

    # TODO: Validate
    @override
    def update_plugin(self, plugin: Plugin) -> None:
        self._plugin_updater().update_plugin(plugin)

    # TODO: Validate
    @override
    def update_source(self, source: Source, update_at: datetime) -> None:
        self._plugin_updater().update_source(source, update_at)

    # TODO: Validate
    @override
    def update_file(self, file: File) -> None:
        self._plugin_updater().update_file(file)

    # TODO: Validate
    @override
    def update_channel(self, channel: Channel) -> None:
        self._plugin_updater().update_channel(channel)

    # TODO: Validate
    @override
    def tmdb_lookup_info(self, title: Title) -> list[TMDBLookupInfo]:
        return self._plugin_linker().tmdb_lookup_info(title)

    # TODO: Validate
    @classmethod
    def _read_instructions_file(cls, file_name: str, default: str) -> str:
        """Return the contents of `file_name` from the plugin's directory."""
        instructions_file = Path(inspect.getfile(cls)).parent / file_name
        if not instructions_file.is_file():
            return default
        return instructions_file.read_text(encoding="utf-8")

    # The markdown file, stored next to the plugin, describing the URLs it supports.
    # TODO: Validate
    @classmethod
    def import_url_instructions_file(cls) -> str:
        return "import_url_instructions.md"

    # TODO: Validate
    @classmethod
    @cache
    def import_url_instructions(cls) -> str:
        """Markdown describing what URLs this plugin supports.

        Read once per plugin from `import_url_instructions_file`, so the examples can be
        edited without touching the plugin. Add that file to include example URLs so
        users know what to paste.
        """
        return cls._read_instructions_file(
            cls.import_url_instructions_file(),
            "This plugin does not have specific URL import instructions.",
        )

    # The markdown file, stored next to the plugin, describing how to export a watch
    # history. Whether a plugin can import one is decided by `import_watch_history`,
    # not by this file existing.
    # TODO: Validate
    @classmethod
    def import_watch_history_instructions_file(cls) -> str:
        return "import_watch_history_instructions.md"

    # TODO: Validate
    @classmethod
    @cache
    def import_watch_history_instructions(cls) -> str:
        """Markdown text describing how to export and upload watch history.

        Read once per plugin from `import_watch_history_instructions_file`, so the steps
        can be edited without touching the plugin.
        """
        return cls._read_instructions_file(
            cls.import_watch_history_instructions_file(),
            "This plugin does not have specific watch history import instructions.",
        )
