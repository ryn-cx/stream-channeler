from __future__ import annotations

from abc import ABC
from typing import TYPE_CHECKING, Any, override

from sqlmodel import Session

from app.media.media_type import TMDBMediaType
from app.plugins.models import Plugin
from app.sources.models import Source
from app.titles.models import Title
from plugins.utils.abstract_plugin import AbstractPlugin, TMDBLookupInfo
from plugins.utils.base_plugin.channels import BaseChannelMixin
from plugins.utils.base_plugin.initialize import BaseInitializeMixin
from plugins.utils.base_plugin.media_importer import BaseMediaImporterMixin
from plugins.utils.base_plugin.media_type import MediaType
from plugins.utils.base_plugin.preload import BasePreloadMixin
from plugins.utils.base_plugin.soft_delete import BaseSoftDeleteMixin
from plugins.utils.base_plugin.update_at import BasePluginUpdateAt
from plugins.utils.base_plugin.url import BaseURLMixin

if TYPE_CHECKING:
    from app.channels.models import Channel
    from plugins.utils.base_plugin.files import BaseFile


# TODO: Validate
class BasePlugin(
    BaseChannelMixin,
    BaseInitializeMixin,
    BaseSoftDeleteMixin,
    BasePluginUpdateAt,
    BasePreloadMixin,
    BaseMediaImporterMixin,
    BaseURLMixin,
    AbstractPlugin,
    ABC,
):
    @override
    def __init__(
        self,
        session: Session,
        plugin: Plugin | None = None,
        file_cache: dict[tuple[type[BaseFile[Any]], Any], BaseFile[Any]] | None = None,
    ) -> None:
        """Initialize the plugin.

        Args:
            session: The SQLAlchemy session to use for database operations.
            plugin: An optional `Plugin` instance to use instead of fetching it from the
            database.
        """
        self.session = session
        self.plugin = plugin or Plugin.get_one(session, self.plugin_name())
        """The `Plugin` record from the database."""
        self._sources = {source.key: source for source in self.plugin.sources}
        """All of the `Source` records from the database in a dict keyed by
        `Source.key`."""
        self._file_cache = file_cache if file_cache is not None else {}

    @classmethod
    def source_name(cls) -> str:
        return cls.plugin_name()

    @classmethod
    def name_on_tmdb(cls) -> tuple[str, ...]:
        """Return the names on TMDB's provider list this plugin supports."""
        return (cls.plugin_name(),)

    @classmethod
    @override
    def matches_tmdb_provider(cls, provider_name: str) -> bool:
        """Return `True` if the the plugin supports the named provider from TMDB."""
        return provider_name in cls.name_on_tmdb()

    def _upsert_title(
        self,
        source: Source,
        title_key: str,
    ) -> Title:
        """Upserts a title completely."""
        msg = f"{self.plugin_name()} does not upsert titles."
        raise NotImplementedError(msg)

    # TODO: Validate
    @override
    def _update_plugin(self, plugin: Plugin) -> None:
        """Update the plugin with the latest data.

        The default implementation assumes that the plugin files contain all of the
        titles available on the website available from the
        `_plugin_files_data_timestamps` function."""
        self._download_if_outdated(self._plugin_files(), plugin.update_at)
        self.create_initial_channel_records()
        data_timestamp = min(self._plugin_files_data_timestamps())
        new_title_keys = self._title_keys_from_plugin_files()
        self._mark_mismatched_titles_as_outdated(None, new_title_keys, data_timestamp)
        plugin.data_timestamp = data_timestamp

    @property
    def source(self) -> Source:
        """Return the source associated with this importer."""
        return self._sources[self.source_name()]

    # TODO: Validate
    @override
    def tmdb_lookup_info(self, title: Title) -> list[TMDBLookupInfo]:
        """Return the TMDB lookup information for the given title."""
        if not title.name:
            msg = f"Title {title.key} has no name"
            raise ValueError(msg)

        media_type = (
            TMDBMediaType.movie
            if title.media_type == MediaType.movie
            else TMDBMediaType.tv
        )
        return [TMDBLookupInfo(title.name, media_type, title.year)]

    @override
    def update_channel(self, channel: Channel) -> None:
        self._remove_queue_entries_with_deleted_titles(channel)
        super().update_channel(channel)
