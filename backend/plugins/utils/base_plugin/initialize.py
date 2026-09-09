# TODO: Validate
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from sqlmodel import Session

from app.models import BaseMediaMixin
from app.plugins.models import Plugin
from app.sources.models import Source
from app.utils import tz_datetime
from plugins.utils.base_plugin.file_access import BaseFileAccessMixin
from plugins.utils.constants import INCOMPLETE_STATUS

if TYPE_CHECKING:
    from datetime import datetime


# TODO: Validate
class BaseInitializeMixin(BaseFileAccessMixin, ABC):
    """Creates the database records a plugin needs before it can be used."""

    _sources: dict[str, Source]

    if TYPE_CHECKING:
        # TODO: Validate
        def __init__(self, session: Session, plugin: Plugin | None = None) -> None: ...

    @classmethod
    @abstractmethod
    def plugin_name(cls) -> str:
        """Return the name of the plugin."""

    @classmethod
    def _source_keys(cls) -> tuple[str, ...]:
        """Return the keys of the sources associated with the plugin."""
        return (cls.plugin_name(),)

    @classmethod
    @abstractmethod
    def favicon_url(cls) -> str:
        """Return the URL of the plugin's favicon."""

    # TODO: Validate
    def link_to_tmdb(self) -> bool:
        """Return whether the plugin should link to TMDB."""
        return True

    @staticmethod
    def _existing_data_timestamp_or_now(record: BaseMediaMixin | None) -> datetime:
        """Return the record's data timestamp, or the current time if it has none."""
        if record and record.data_timestamp:
            return record.data_timestamp
        return tz_datetime.now()

    # TODO: Validate
    def upsert_source(self, source_key: str) -> Source:
        """Create or update the plugin's `Source` record(s)."""
        existing_source = Source.get_from_memory(self.session, self.plugin, source_key)
        data_timestamp: datetime
        try:
            self._source_files()
        except NotImplementedError:
            data_timestamp = self._existing_data_timestamp_or_now(existing_source)
        else:
            data_timestamp = self._source_files_data_timestamp()
        source = Source(
            key=source_key,
            favicon_url=self.favicon_url(),
            link_to_tmdb=self.link_to_tmdb(),
            data_timestamp=data_timestamp,
            plugin_id=self.plugin.id,
        ).upsert(self.plugin, existing_source)
        source.set_update_at(None)
        return source

    @classmethod
    def initialize_plugin(cls, session: Session) -> None:
        """Initialize the plugin by creating it's base database records.

        Calls `_create_initial_plugin_record`, `_create_initial_source_records` and
        `_create_initial_channel_records`."""
        plugin = Plugin.get(session, cls.plugin_name())
        if plugin and plugin.status != INCOMPLETE_STATUS:
            return

        if not plugin:
            plugin = cls._create_initial_plugin_record(session)
        plugin_initializator = cls(session, plugin)
        plugin_initializator._create_initial_source_records()
        plugin_initializator._create_initial_channel_records()
        plugin_initializator.plugin.status = None

    @classmethod
    def _create_initial_plugin_record(cls, session: Session) -> Plugin:
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

    def _create_initial_source_records(self) -> None:
        """Create the initial source records for the plugin.

        Automatically called during plugin initialization."""
        for source_key in self._source_keys():
            if Source.get(self.session, self.plugin, source_key) is None:
                self.upsert_source(source_key)
        self._sources = {source.key: source for source in self.plugin.sources}

    # TODO: Validate
    def _create_initial_channel_records(self) -> None:
        """Create the initial channel records for the plugin.

        Automatically called during plugin initialization."""
