# TODO: Validate
from __future__ import annotations

from abc import ABC

from sqlmodel import Session

from app.plugins.models import Plugin
from app.sources.models import Source
from plugins.utils.base_plugin_v2.base import PluginBase


# TODO: Validate
class PluginInitializer(PluginBase, ABC):
    # TODO: Validate
    @classmethod
    def initialize_db(cls, session: Session) -> None:
        plugin = cls.initialize_plugin(session)
        cls.initialize_sources(session, plugin)

    # TODO: Validate
    @classmethod
    def initialize_plugin(cls, session: Session) -> Plugin:
        plugin = Plugin.get(session, cls.plugin_name())
        if plugin is not None:
            return plugin

        with Session(session.get_bind()) as plugin_session:
            Plugin(
                key=cls.plugin_name(),
            ).upsert_and_set_update_at(
                plugin_session,
                Plugin.get(plugin_session, cls.plugin_name()),
            )
            plugin_session.commit()
        return Plugin.get_one(session, cls.plugin_name())

    # TODO: Validate
    @classmethod
    def initialize_sources(cls, session: Session, plugin: Plugin) -> None:
        for source_key in cls._source_keys():
            if Source.get(session, plugin, source_key) is None:
                cls._upsert_source(session, plugin, source_key)
