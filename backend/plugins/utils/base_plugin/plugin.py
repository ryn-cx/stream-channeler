# TODO: Validate
from __future__ import annotations

import inspect
from abc import ABC, abstractmethod
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any, Self, cast, override

from loguru import logger
from sqlmodel import Session

from app.episodes.models import Episode
from app.episodes.preload import preload_episodes
from app.media.media_type import MediaType
from app.models import BaseMediaMixin
from app.plugins.models import Plugin
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from app.utils import tz_datetime
from plugins.utils.abstract_plugin import (
    AbstractPlugin,
    InvalidURLError,
    PluginShowIdentity,
    URLImportResult,
)
from plugins.utils.base_plugin.check import CheckMixin
from plugins.utils.base_plugin.context import (
    PluginContext,
    plugin_context,
    store_plugin_context,
)
from plugins.utils.base_plugin.files import INITIAL_FILE_IDENTIFIER, BaseFile
from plugins.utils.base_plugin.preload import PreloadMixin
from plugins.utils.base_plugin.url import URLMixin
from plugins.utils.base_plugin.watch import WatchMixin
from plugins.utils.manage_plugins import register_plugins

_TMDB_MEDIA_TYPES = {
    "Movie": MediaType.movie,
    "Series": MediaType.tv,
    "TV Show": MediaType.tv,
}
"""Which TMDB media type each of a show's own media types is searched under.

A media type TMDB has no half of - a channel, a video, a concert - is not
searched for at all.
"""


# TODO: Validate
class BasePlugin(
    PreloadMixin,
    CheckMixin,
    URLMixin,
    WatchMixin,
    AbstractPlugin,
    ABC,
):
    session: Session
    _context: PluginContext
    _file_cache: dict[object, Any]

    # TODO: Validate
    def __init__(self, session: Session) -> None:
        self.session = session
        self._file_cache = {}
        if (context := plugin_context(session, self.plugin_key())) is None:
            self._context = self._load_context()
            store_plugin_context(session, self.plugin_key(), self._context)
        else:
            self._context = context

    # TODO: Validate
    def _load_context(self) -> PluginContext:
        plugin = Plugin.get(self.session, self.plugin_key())
        if plugin is None:
            msg = f"{self.plugin_key()} has not been initialized."
            raise RuntimeError(msg)

        context = PluginContext(plugin=plugin)
        for source_key in self._source_keys():
            source = Source.get(self.session, plugin, source_key)
            if source is not None:
                context.sources[source_key] = source
        return context

    # TODO: Validate
    def __init_subclass__(cls, *, register: bool = True, **kwargs: Any) -> None:  # noqa: ANN401 - Handed straight to `super`.
        """Auto-register every concrete subclass as a plugin.

        Pass `register=False` in the subclass declaration to opt out. That's
        used for intermediate mixin classes that shouldn't appear as their own
        plugin in the registry.
        """
        super().__init_subclass__(**kwargs)
        if register:
            register_plugins(cast("type[AbstractPlugin]", cls))

    # TODO: Validate
    @classmethod
    def plugin_key(cls) -> str:
        return cls.__name__

    # TODO: Validate
    @classmethod
    def plugin_name(cls) -> str:
        """Return the name of the plugin."""
        return cls.__name__

    # TODO: Validate
    @classmethod
    def implements(cls, method_name: str) -> bool:
        """Return True when the subclass has overridden `method_name`."""
        child_implementation = inspect.getattr_static(cls, method_name)
        core_implementation = inspect.getattr_static(BasePlugin, method_name)
        return child_implementation is not core_implementation

    # TODO: Validate
    @classmethod
    @abstractmethod
    def favicon_url(cls) -> str | None: ...

    # TODO: Validate
    @classmethod
    @override
    def url_regex(cls) -> str:
        msg = f"{cls.plugin_key()} does not read URLs."
        raise NotImplementedError(msg)

    # TODO: Validate
    @classmethod
    def manual_search(cls, query: str) -> str | None:  # noqa: ARG003 - `query` is used by overrides.
        """Return the plugin website's own search-page URL for `query`."""
        return None

    # TODO: Validate
    def search(self, query: str) -> str | None:
        """Return the address of the one title `query` names here, or None."""
        msg = "search is not supported by this plugin."
        raise NotImplementedError(msg)

    # TODO: Validate
    def show_identity(self, show_key: str) -> PluginShowIdentity:
        """Return the name, media type and year the plugin files a show under.

        Args:
            show_key: The plugin's own key for the show.

        """
        msg = "show_identity is not supported by this plugin."
        raise NotImplementedError(msg)

    # The names TMDB uses for this plugin's website in its watch-provider data.
    # A plugin may map to several (e.g. Netflix's base and ad-supported tiers);
    # empty when the plugin has no matching TMDB provider.
    # TODO: Validate
    @classmethod
    def tmdb_provider_names(cls) -> tuple[str, ...]:
        return ()

    # TODO: Validate
    @classmethod
    def matches_tmdb_provider(cls, provider_name: str) -> bool:
        folded_name = provider_name.casefold()
        return any(folded_name == name.casefold() for name in cls.tmdb_provider_names())

    # TODO: Validate
    @classmethod
    def _plugin_wide_files(cls) -> tuple[type[BaseFile[Any]], ...]:
        """The file types that describe the plugin or a source rather than one show.

        `_file` caches these against the session rather than against one view of
        the plugin, since re-reading a provider list or a feed for every show
        would be wasted work.
        """
        return ()

    # TODO: Validate
    def _canonical_source(self) -> Source:
        """Return the `Source` the canonical rows this plugin creates belong to.

        Keyed by the plugin rather than by any of the websites it reads, because
        the canonical rows it mints are keyed the same way and one of them is
        stood for by listings from every provider the plugin tracks. Picking one
        of those providers would be picking whichever was imported first.
        """
        if self._context.canonical_source is not None:
            return self._context.canonical_source

        source = Source.get(self.session, self.plugin, self.plugin_key())
        if source is None:
            source = Source(
                key=self.plugin_key(),
                name=self.plugin_name(),
                plugin_id=self.plugin.id,
            ).upsert(self.plugin, None)
        self._context.canonical_source = source
        return source

    # TODO: Validate
    @classmethod
    @override
    def initialize_db(cls, session: Session) -> None:
        cls.create_plugin_db_entry(session)
        cls(session).initialize_sources()

    # TODO: Validate
    def initialize_sources(self) -> None:
        """Create the `Source` record(s) and set `self.source`."""
        self.initialize_source(self.plugin_key(), self._upsert_source)


    # TODO: Validate
    def _upsert_source(self, *args: Any, **kwargs: Any) -> Source:  # noqa: ANN401 - Child signatures vary.
        """Create or update the plugin's `Source` record(s)."""
        msg = f"{self.plugin_key()} does not implement _upsert_source."
        raise NotImplementedError(msg)

    # TODO: Validate
    def initialize_source(
        self,
        source_key: str,
        build_source: Callable[[], Source],
    ) -> None:
        if source_key in self._sources:
            return

        existing_source = Source.get(self.session, self.plugin, source_key)
        self._sources[source_key] = existing_source or build_source()

    # TODO: Validate
    @classmethod
    @override
    def create_plugin_db_entry(cls, session: Session) -> None:
        if Plugin.get(session, cls.plugin_key()):
            return

        with Session(session.get_bind()) as plugin_session:
            Plugin(
                key=cls.plugin_key(),
                name=cls.plugin_name(),
            ).upsert_and_set_update_at(
                plugin_session,
                Plugin.get(plugin_session, cls.plugin_key()),
            )
            plugin_session.commit()
        if Plugin.get(session, cls.plugin_key()) is None:
            msg = f"{cls.plugin_key()} could not be written."
            raise RuntimeError(msg)

    # TODO: Validate
    def _fresh(self) -> Self:
        """Return a second view over the same session, for another show.

        A plugin caches what it reads for the show it is working on, which the
        next show must not read. The next show gets a view of its own and the
        last one's is let go with it. What the plugin knows about itself is held
        by the session rather than by the view, so a view costs nothing to make.
        """
        return type(self)(self.session)

    # TODO: Validate
    @property
    def plugin(self) -> Plugin:
        return self._context.plugin

    # TODO: Validate
    @property
    def _sources(self) -> dict[str, Source]:
        return self._context.sources

    # TODO: Validate
    @property
    def _reusable_file_cache(self) -> dict[object, Any]:
        return self._context.reusable_files

    # TODO: Validate
    @property
    def source(self) -> Source:
        """Return the plugin's `Source` record or raise if not initialized."""
        return self._source_db_entry(self.plugin_key())

    # TODO: Validate
    @property
    def has_source(self) -> bool:
        """Return True if the plugin has a `Source` record."""
        return self.plugin_key() in self._sources

    # TODO: Validate
    def _source_db_entry(self, source_key: str) -> Source:
        if source_key not in self._sources:
            msg = f"Source {source_key} has not been initialized."
            raise AttributeError(msg)
        return self._sources[source_key]

    # TODO: Validate
    @classmethod
    def _source_keys(cls) -> tuple[str, ...]:
        return (cls.plugin_key(),)

    # TODO: Validate
    @staticmethod
    def _existing_data_timestamp_or_now(record: BaseMediaMixin | None) -> datetime:
        """Return the record's data timestamp, or the current time if it has none."""
        if record and record.data_timestamp:
            return record.data_timestamp
        return tz_datetime.now()

    # TODO: Validate
    def _set_weekly_updates_from_episodes(
        self,
        show: Show,
        *,
        update_show: bool = True,
        update_seasons: bool = True,
    ) -> None:
        """Set update_at on the `Show`/`Season` based on `Episode.air_date`.

        `update_at` will be set to be a week after the latest `Episode.air_date` if
        that is a better `update_at` value than the current `update_at` value.
        """
        preload_episodes(self.session, [show])
        for season in show.active_children:
            for episode in season.active_children:
                if episode.air_date:
                    update_at = episode.air_date + timedelta(days=7)
                    if update_seasons:
                        season.set_update_at(update_at)
                    if update_show:
                        show.set_update_at(update_at)

    # TODO: Validate
    def _update_and_upsert_show(
        self,
        show: Show,
        update_at: datetime | None = None,
        *,
        force: bool = False,
    ) -> None:
        """Read a stored listing again, and settle what its episodes are linked to.

        An update writes the same episodes an import does, so which TMDB episode
        each of them is is worked out here too. Only the matching, and not the
        rest of what an import settles: which title a listing is linked to is
        read off a website's own account of itself, which an update is not
        reading, and a canonical row has no title to point at at all.
        """
        _cache = self._download_show_files_and_children(show, update_at)
        self._preload_show(show.id, preload_episodes=True).one()
        self.upsert_show(show.source, show.key, force=force)

    # TODO: Validate
    @override
    def update_show(self, show: Show, *, force: bool = False) -> None:
        source_name = show.source.name or show.source.key
        show_name: str
        if show.name:
            show_name = f"{show.name} ({show.key})"
        else:
            show_name = show.key
        logger.info("Updating show: {} - {}", source_name, show_name)
        show = self._preload_show(show.key, source_key=show.source.key).one()
        self._update_and_upsert_show(show, show.update_at, force=force)

    # TODO: Validate
    @override
    def update_season(self, season: Season) -> None:
        logger.info("Updating season: {}", season.key)
        season = self._preload_season(season.id, preload_show=True).one()
        self._download_season_files_and_children(season, update_at=season.update_at)
        self._update_and_upsert_show(season.show)

    # TODO: Validate
    @override
    def update_episode(self, episode: Episode) -> None:
        logger.info("Updating episode: {}", episode.key)
        episode = self._preload_episode(episode.id, preload_source=True).one()
        self._download_episode_files(episode, update_at=episode.update_at)
        self._update_and_upsert_show(episode.season.show)

    # TODO: Validate
    @override
    def on_update_plugin_failure(self, plugin: Plugin, error: Exception) -> None:
        plugin.update_at = tz_datetime.max()

    # TODO: Validate
    @override
    def on_update_source_failure(self, source: Source, error: Exception) -> None:
        source.update_at = tz_datetime.max()

    # TODO: Validate
    @override
    def on_update_show_failure(self, show: Show, error: Exception) -> None:
        show.update_at = tz_datetime.max()

    # TODO: Validate
    @override
    def on_update_season_failure(self, season: Season, error: Exception) -> None:
        season.update_at = tz_datetime.max()

    # TODO: Validate
    @override
    def on_update_episode_failure(self, episode: Episode, error: Exception) -> None:
        episode.update_at = tz_datetime.max()

    # TODO: Validate
    def _upsert_show_object(
        self,
        show: Show,
        source: Source,
        existing_show: Show | None,
        show_key: str,
    ) -> Show:
        """Store the source's own `Show` against the files it was read out of.

        A show built fresh off the source's files knows nothing of the canonical
        shows the stored one is linked to. Those are rows of `ShowCanonicalShow`
        rather than columns here, so there is nothing to write away and nothing to
        carry over: which canonical show it is linked to is settled once its
        episodes are written, which is where `upsert_show` ends.
        """
        show_files = self._show_files(show_key)
        return show.upsert_and_set_update_at(source, existing_show, show_files)

    # TODO: Validate
    def _upsert_season_object(
        self,
        season: Season,
        show: Show,
        existing_season: Season | None,
        show_key: str,
    ) -> Season:
        """Store the website's own `Season` against the files it was read out of."""
        season_files = self._season_files(season.key, show_key)
        return season.upsert_and_set_update_at(show, existing_season, season_files)

    # TODO: Validate
    def _upsert_episode_object(
        self,
        episode: Episode,
        season: Season,
        existing_episode: Episode | None,
        show_key: str,
    ) -> Episode:
        """Store the website's own `Episode` against the files it was read out of.

        The links the stored record carries are rows of their own and stay where
        they are, so nothing here has to carry them over. The note travels with
        them: how a link came to be made is most of what says whether it should
        be kept, so an episode that keeps its links keeps the reason for them
        too.
        """
        if existing_episode:
            episode.canonical_episode_note = existing_episode.canonical_episode_note
        episode_files = self._episode_files(episode.key, season.key, show_key)
        return episode.upsert_and_set_update_at(season, existing_episode, episode_files)

    # TODO: Validate
    @abstractmethod
    def upsert_show(
        self,
        source: Source,
        show_key: str,
        canonical_show: Show | None = None,
        *,
        force: bool = False,
    ) -> Show:
        """Store the listing `show_key` names, and settle what it stands for.

        Every plugin ends this by handing what it wrote to `settle_show`, which is
        what settles the title the listing is linked to. Done there rather than
        by whatever called, because it is part of writing a listing, and done at
        the end rather than as the row is written, since the episodes read
        against the title are the ones the write has just put there.

        `canonical_show` is the title a caller already knows the listing to be,
        which is what an import handing a title from one plugin to another knows
        and nothing else does.
        """


    # TODO: Validate
    def soft_delete_missing_seasons(self, show_key: str) -> None:
        """Soft-delete seasons whose keys are not in the show's season file."""
        season_keys = self._season_keys_from_file(show_key)
        source_ids = {source.id for source in self.plugin.sources}
        for obj in list(self.session.identity_map.values()):
            if (
                isinstance(obj, Show)
                and obj.key == show_key
                and obj.source_id in source_ids
            ):
                obj.soft_delete_missing_children(season_keys)

    # TODO: Validate
    def soft_delete_missing_episodes(self, season_key: str, show_key: str) -> None:
        """Soft-delete episodes whose keys are not in the season's episode file."""
        episode_keys = self._episode_keys_from_file(season_key, show_key)
        source_ids = {source.id for source in self.plugin.sources}
        show_ids = {
            obj.id
            for obj in self.session.identity_map.values()
            if isinstance(obj, Show) and obj.source_id in source_ids
        }
        for obj in list(self.session.identity_map.values()):
            if (
                isinstance(obj, Season)
                and obj.key == season_key
                and obj.show_id in show_ids
            ):
                obj.soft_delete_missing_children(episode_keys)

    # TODO: Validate
    def _soft_delete_missing(self, show_key: str) -> None:
        _cache = self._preload_show(show_key, preload_episodes=True).all()
        self.soft_delete_missing_seasons(show_key)
        for season_key in self._season_keys_from_file(show_key):
            self.soft_delete_missing_episodes(season_key, show_key)

    # TODO: Validate
    def _file[FileT: BaseFile[Any]](
        self,
        file_type: Callable[..., FileT],
        *identifiers: object,
    ) -> FileT:
        """Return the cached `file_type` instance for `identifiers`."""
        cache = (
            self._reusable_file_cache
            if file_type in self._plugin_wide_files()
            else self._file_cache
        )
        cache_key = (file_type, identifiers)
        if cached := cache.get(cache_key):
            return cached
        file = file_type(self.session, self.plugin, *identifiers)
        cache[cache_key] = file
        return file

    # TODO: Validate
    def _initial_file[FileT: BaseFile[Any]](
        self,
        file_type: Callable[..., FileT],
    ) -> FileT:
        """Return the `file_type` instance a timestamped series of files starts at."""
        return self._file(file_type, INITIAL_FILE_IDENTIFIER)

    # TODO: Validate
    def _tmdb_show(self, show_key: str, *, force: bool = False) -> Show | None:
        if not self.implements("show_identity"):
            return None

        identity = self.show_identity(show_key)

        media_type = _TMDB_MEDIA_TYPES.get(identity.media_type)
        if media_type is None:
            return None

        from plugins.TMDB import TMDB  # noqa: PLC0415

        return TMDB(self.session).import_search(
            identity.title,
            media_type,
            identity.year,
            force=force,
        )

    # TODO: Validate
    def raise_if_invalid_file(self, file: BaseFile[Any], url: str) -> None:
        file.download_if_outdated()
        if not file.database_record.content:
            msg = f"Invalid {self.plugin_key()} URL: {url}"
            raise InvalidURLError(msg)


# TODO: Validate
class ReadURLPlugin(BasePlugin, ABC, register=False):
    _show_key: str

    # TODO: Validate
    @classmethod
    @abstractmethod
    def _url_regexes(cls) -> tuple[str, ...]: ...

    # TODO: Validate
    @classmethod
    @override
    def url_regex(cls) -> str:
        domain_regex = cls._domain_regex()
        alternatives = "|".join(
            domain_regex + url_regex for url_regex in cls._url_regexes()
        )
        return f"(?:{alternatives})"

    # TODO: Validate
    @abstractmethod
    def _parse_url(self, url: str) -> None: ...

    # TODO: Validate
    def _url_source(self) -> Source:
        return self.source

    # TODO: Validate
    def _import_results(self, show: Show) -> list[URLImportResult]:
        results = [URLImportResult.show_import_results(show)]
        results += [
            URLImportResult.show_import_results(canonical_show)
            for canonical_show in show.canonical_shows
        ]
        return results

    # TODO: Validate
    def _import_read_url(
        self,
        canonical_show: Show | None = None,
        *,
        force: bool = False,
    ) -> list[URLImportResult]:
        show_key = self._show_key
        if not force and (show := self._preload_show(show_key).one_or_none()):
            return self._import_results(show)

        _cache = self._download_show_files_and_children(show_key)
        if canonical_show is None:
            canonical_show = self._tmdb_show(show_key, force=force)
            if not force and (show := self._preload_show(show_key).one_or_none()):
                return self._import_results(show)

        show = self.upsert_show(
            self._url_source(),
            show_key,
            canonical_show=canonical_show,
            force=force,
        )
        return self._import_results(show)

    # TODO: Validate
    @override
    def import_url(
        self,
        url: str,
        canonical_show: Show | None = None,
        *,
        force: bool = False,
    ) -> list[URLImportResult]:
        self._parse_url(url)
        return self._import_read_url(canonical_show, force=force)
