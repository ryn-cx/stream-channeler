from __future__ import annotations

from abc import ABC

from sqlmodel import Session

from app.plugins.models import Plugin
from app.sources.models import Source
from plugins.utils.base_plugin_v3.base import BasePlugin


class BasePluginInitializer(BasePlugin, ABC):
    # TODO: Validate
    @classmethod
    def initialize_plugin(cls, session: Session) -> None:
        """Initialize the plugin by creating it's base database records.

        Calls `_create_plugin_record`, `create_source_records` and
        `create_channel_records`."""
        plugin = Plugin.get(session, cls.plugin_name())
        if plugin and plugin.status != "Incomplete":
            return

        if not plugin:
            plugin = cls._create_plugin_record(session)
        plugin_initializator = cls(session, plugin)
        plugin_initializator._create_source_records()
        plugin_initializator._create_channel_records()
        plugin_initializator.plugin.status = None

    @classmethod
    def _create_plugin_record(cls, session: Session) -> Plugin:
        """Create the plugin record for the plugin."""
        if plugin := Plugin.get(session, cls.plugin_name()):
            return plugin

        # Commit the plugin to the database because initialize_sources will be called
        # after this and some plugins require files to be downloaded which requires the
        # plugin to exist in the database because files are automatically commited on
        # download completion.
        with Session(session.get_bind()) as plugin_session:
            plugin = Plugin(key=cls.plugin_name(), status="Incomplete")
            plugin.upsert_and_set_update_at(plugin_session, None)
            plugin_session.commit()

        # The plugin returned needs to be for the original session because the other
        # session has been closed.
        return Plugin.get_one(session, cls.plugin_name())

    def _create_source_records(self) -> None:
        """Create the source records for the plugin."""
        for source_key in self._source_keys():
            if Source.get(self.session, self.plugin, source_key) is None:
                self.upsert_source(source_key)
        self._sources = {source.key: source for source in self.plugin.sources}

    def _create_channel_records(self) -> None:
        """Create the channel records for the plugin."""
