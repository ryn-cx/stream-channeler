# TODO: Validate
from __future__ import annotations

from abc import ABC

from sqlmodel import Session

from app.plugins.models import Plugin
from app.sources.models import Source
from plugins.utils.base_plugin_v2.base import BasePlugin


# TODO: Validate
class BasePluginInitializer(BasePlugin, ABC):
    # TODO: Validate
    @classmethod
    def initialize_db(cls, session: Session) -> None:
        """Initialize the database for the plugin.

        Calls `initialize_plugin`, `initialize_sources` and `initialize_channels`."""
        plugin = Plugin.get(session, cls.plugin_name())
        if plugin and plugin.status != "Incomplete":
            return

        cls._initialize_plugin(session)
        plugin_initializator = cls(session)
        plugin_initializator._initialize_sources()
        plugin_initializator._initialize_channels()
        plugin_initializator.plugin.status = None

    # TODO: Validate
    @classmethod
    def _initialize_plugin(cls, session: Session) -> Plugin:
        if plugin := Plugin.get(session, cls.plugin_name()):
            return plugin

        # Commit the plugin to the database because initialize_sources will be called
        # after this and some plugins require files to be downloaded to initialize the
        # sources.
        with Session(session.get_bind()) as plugin_session:
            plugin = Plugin(key=cls.plugin_name(), status="Incomplete")
            plugin.upsert_and_set_update_at(plugin_session, None)
            plugin_session.commit()

        # The plugin returned needs to be for the original session because the other
        # session has been closed.
        return Plugin.get_one(session, cls.plugin_name())

    # TODO: Validate
    def _initialize_sources(self) -> None:
        """Create the sources in the database for the plugin."""
        for source_key in self._source_keys():
            if Source.get(self.session, self.plugin, source_key) is None:
                self.upsert_source(source_key)
        self._sources = {source.key: source for source in self.plugin.sources}

    def _initialize_channels(self) -> None:
        """Create the channels in the database for the plugin."""
