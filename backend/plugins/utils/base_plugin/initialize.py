from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from sqlmodel import Session

from app.plugins.models import Plugin
from app.sources.models import Source
from plugins.utils.base_plugin.core import BasePluginCore
from plugins.utils.constants import INCOMPLETE_STATUS

if TYPE_CHECKING:
    from datetime import datetime


# TODO: Validate
class BaseInitializeMixin(BasePluginCore, ABC):
    """Creates the database records a plugin needs before it can be used."""

    HIDDEN: bool = False

    @classmethod
    def _source_keys(cls) -> tuple[str, ...]:
        """Return the keys of the sources associated with the plugin.

        Used to create the initial source records for the plugin."""
        return (cls.plugin_name(),)

    # TODO: Validate
    @classmethod
    def initialize_plugin(cls, session: Session) -> None:
        """Initialize the plugin by creating it's base database records.

        Calls `_create_initial_plugin_record`, `_create_initial_source_records` and
        `_create_initial_channel_records`."""
        plugin = Plugin.get(session, cls.plugin_name())
        if plugin and plugin.status != INCOMPLETE_STATUS:
            return

        if not plugin:
            plugin = cls.create_initial_plugin_record(session)
        plugin_initializator = cls(session, plugin)
        plugin_initializator.create_initial_source_records()
        plugin_initializator.create_initial_channel_records()
        plugin_initializator.plugin.update_at = (
            plugin_initializator._next_plugin_update_at()
        )
        plugin_initializator.plugin.hidden = cls.HIDDEN
        plugin_initializator.plugin.status = None

    @classmethod
    def create_initial_plugin_record(cls, session: Session) -> Plugin:
        """Create the plugin record for the plugin.

        Automatically called during plugin initialization."""
        if plugin := Plugin.get(session, cls.plugin_name()):
            return plugin

        # Commit the plugin to the database because initialize_sources will be called
        # after this and some plugins require files to be downloaded which requires the
        # plugin to exist in the database because files are automatically commited on
        # download completion.
        with Session(session.get_bind()) as plugin_session:
            plugin = Plugin(key=cls.plugin_name(), status=INCOMPLETE_STATUS)
            plugin.upsert(plugin_session, None)
            plugin_session.commit()

        # The plugin returned needs to be for the original session because the other
        # session has been closed.
        return Plugin.get_one(session, cls.plugin_name())

    def create_initial_source_records(self) -> None:
        """Create the initial source records for the plugin.

        Automatically called during plugin initialization."""
        for source_key in self._source_keys():
            if Source.get(self.session, self.plugin, source_key) is None:
                self.upsert_source(source_key)
        self._sources = {source.key: source for source in self.plugin.sources}

    # TODO: Validate
    @abstractmethod
    def create_initial_channel_records(self) -> None: ...

    # TODO: Validate
    def _next_plugin_update_at(self) -> datetime | None:
        return None
