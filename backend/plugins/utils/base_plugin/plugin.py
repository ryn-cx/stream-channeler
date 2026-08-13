# TODO: Validate
from __future__ import annotations

import re
from abc import ABC, abstractmethod
from collections.abc import Callable, Iterable
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, ClassVar, cast, override

from loguru import logger
from sqlmodel import Session

from app.canonical_media.service import link_canonical_show
from app.episodes.models import Episode
from app.models import BaseMediaMixin, Visibility
from app.plugins.models import Plugin
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from app.users.models import User
from app.users.service import get_or_create_plugin_user
from app.utils import tz_datetime
from plugins.utils.abstract_plugin import (
    AbstractPlugin,
    InvalidURLError,
    URLImportResult,
)
from plugins.utils.base_plugin.check import CheckMixin
from plugins.utils.base_plugin.files import INITIAL_FILE_IDENTIFIER, BaseFile
from plugins.utils.base_plugin.preload import PreloadMixin
from plugins.utils.base_plugin.url import URLHandler, URLMixin
from plugins.utils.base_plugin.watch import WatchMixin

# The entry points that work on a single show, mapped to the name of their first
# argument and how the show is read off it. `import_url` has no show until the
# plugin has parsed the URL, so the URL stands in for it.
_ENTRY_POINTS: dict[str, tuple[str, Callable[[Any], str]]] = {
    "import_url": ("url", lambda url: url),
    "update_show": ("show", lambda show: show.key),
    "update_season": ("season", lambda season: season.show.key),
    "update_episode": ("episode", lambda episode: episode.season.show.key),
}


# TODO: Validate
def _tracks_show(
    entry_point: Callable[..., Any],
    argument: str,
    show_of: Callable[[Any], str],
) -> Callable[..., Any]:
    """Return `entry_point` wrapped so it records the show it was called for."""

    # TODO: Validate
    @wraps(entry_point)
    def tracked(self: BasePlugin, *args: Any, **kwargs: Any) -> Any:  # noqa: ANN401 - Forwarded verbatim.
        entity = args[0] if args else kwargs[argument]
        self._set_current_show(show_of(entity))
        return entry_point(self, *args, **kwargs)

    return tracked


# TODO: Validate
class BasePlugin(
    PreloadMixin,
    CheckMixin,
    URLMixin,
    WatchMixin,
    AbstractPlugin,
    ABC,
    register=False,
):
    _VERSION: str

    _current_show: str | None = None
    """What the values cached on this instance belong to."""

    _file_cache: dict[object, Any]
    _reusable_file_cache: dict[object, Any]

    _PLUGIN_WIDE_FILES: ClassVar[tuple[type[BaseFile[Any]], ...]] = ()
    """The file types that describe the plugin or a source rather than one show.

    `_file` caches these separately so they survive a change of show, since
    re-reading a provider list or a feed for every show would be wasted work.
    """

    SHOW_INDEPENDENT_ATTRIBUTES: ClassVar[frozenset[str]] = frozenset(
        {
            "session",
            "plugin",
            "_source",
            "_current_show",
            "_reusable_file_cache",
        },
    )
    """The instance attributes that describe the plugin rather than a show.

    Everything else is dropped by `_reset_show_state`, so an attribute only
    survives a change of show by being named here.
    """

    # TODO: Validate
    @override
    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Wrap the entry points a subclass declares so they record the show."""
        super().__init_subclass__(**kwargs)
        cls._track_show_on_entry_points()

    # TODO: Validate
    @classmethod
    def _track_show_on_entry_points(cls) -> None:
        """Wrap the entry points this class declares so they record the show.

        Only the definitions in `cls` itself are wrapped, so each one is wrapped
        exactly once and an inherited entry point keeps the wrapper of the class
        that declared it.
        """
        for name, (argument, show_of) in _ENTRY_POINTS.items():
            entry_point = cls.__dict__.get(name)
            if entry_point is None:
                continue
            setattr(cls, name, _tracks_show(entry_point, argument, show_of))

    # TODO: Validate
    def _set_current_show(self, show: str) -> None:
        """Record which show the instance is working on, dropping the last one's.

        Plugins cache values for the show they are working on, which the next
        show must not read. Moving to a different show drops them, so a single
        instance can be used for any number of shows without carrying the
        previous show's data or holding on to it.

        Called by the wrapper `__init_subclass__` puts around every entry point,
        so a plugin cannot miss it by overriding one. An entry point that spans
        several shows, like `update_source`, has to call this itself for each.
        """
        if self._current_show == show:
            return
        # The first call has no earlier show to drop, so whatever construction
        # cached is kept rather than thrown away before it has been read.
        if self._current_show is not None:
            self._reset_show_state()
        self._current_show = show

    # TODO: Validate
    def _reset_show_state(self) -> None:
        """Drop everything cached for the show the instance has moved off.

        Every instance attribute goes except the ones named in
        `SHOW_INDEPENDENT_ATTRIBUTES`, so a plugin caches whatever it likes
        without having to remember to clear it. An attribute that is read after
        being dropped falls back to its class-level default, which is where a
        per-show value's "nothing cached yet" state belongs.
        """
        for name in list(vars(self)):
            if name not in self.SHOW_INDEPENDENT_ATTRIBUTES:
                delattr(self, name)
        self._file_cache = {}

    # TODO: Validate
    @override
    def __init__(self, session: Session) -> None:
        self.session = session
        self._source: Source | None = None
        self._reusable_file_cache = {}
        # Creates the show file cache, which `initialize_database` needs below.
        self._reset_show_state()
        self.initialize_database()
        self._validate_plugin_version()

    # TODO: Validate
    @property
    def source(self) -> Source:
        """Return the plugin's `Source` record or raise if not initialized."""
        if self._source is None:
            msg = "Source has not been initialized."
            raise AttributeError(msg)
        return self._source

    # TODO: Validate
    @source.setter
    def source(self, value: Source) -> None:
        self._source = value

    # TODO: Validate
    @property
    def has_source(self) -> bool:
        """Return True if the plugin has a `Source` record."""
        return self._source is not None

    # TODO: Validate
    def initialize_database(self) -> None:
        """Create the `Plugin` and its `Source` record(s) and set instance attributes.

        Sets `self.plugin` if only a single `Plugin` record exists.
        Sets `self.source` if only a single `Source` record exists.
        """
        self.initialize_plugin()
        self.initialize_sources()

    # TODO: Validate
    def initialize_plugin(self) -> None:
        """Create the `Plugin` record(s) and set `self.plugin`.

        A newly created row is committed before anything else happens. A file
        download writes through a session of its own, so that it is kept even
        when the import that triggered it fails, and a session of its own cannot
        see a `Plugin` this one has not committed yet. Nothing else is pending
        this early, so the commit carries only the plugin.
        """
        if hasattr(self, "plugin") and self.plugin:
            return
        plugin_user = get_or_create_plugin_user(session=self.session)
        if existing_plugin := Plugin.get(self.session, plugin_user, self.plugin_key()):
            self.plugin = existing_plugin
        else:
            self.plugin = self._upsert_plugin(plugin_user, existing_plugin)
            self.session.commit()

    # TODO: Validate
    def initialize_sources(self) -> None:
        """Create the `Source` record(s) and set `self.source`."""
        if hasattr(self, "source") and self.source:
            return

        self.source = (
            Source.get(self.session, self.plugin, self.plugin_key())
            or self._upsert_source()
        )

    # TODO: Validate
    def _upsert_plugin(
        self,
        plugin_user: User,
        existing_plugin: Plugin | None,
    ) -> Plugin:
        """Create or update the `Plugin` record."""
        return Plugin(
            key=self.plugin_key(),
            name=self.plugin_name(),
            version=self._VERSION,
            visibility=Visibility.unlisted,
            anonymous=False,
            user_id=plugin_user.id,
        ).upsert_and_set_update_at(plugin_user, existing_plugin)

    # TODO: Validate
    @staticmethod
    def _existing_data_timestamp_or_now(record: BaseMediaMixin | None) -> datetime:
        """Return the record's data timestamp, or the current time if it has none."""
        if record and record.data_timestamp:
            return record.data_timestamp
        return tz_datetime.now()

    # TODO: Validate
    @staticmethod
    def _set_weekly_updates_from_episodes(
        show: Show,
        *,
        update_show: bool = True,
        update_seasons: bool = True,
    ) -> None:
        """Set update_at on the `Show`/`Season` based on `Episode.air_date`.

        `update_at` will be set to be a week after the latest `Episode.air_date` if
        that is a better `update_at` value than the current `update_at` value.
        """
        for season in show.active_children:
            for episode in season.active_children:
                if episode.air_date:
                    update_at = episode.air_date + timedelta(days=7)
                    if update_seasons:
                        season.set_update_at(update_at)
                    if update_show:
                        show.set_update_at(update_at)

    # TODO: Validate
    def _validate_plugin_version(self) -> None:
        if self.plugin.version != self._VERSION:
            msg = (
                f"Plugin {self.plugin_key()!r} requires version {self._VERSION!r} "
                f"but the database has version {self.plugin.version!r}. "
                f"The database record needs to be migrated."
            )
            raise RuntimeError(msg)

    # TODO: Validate
    def _preload_and_upsert_show(
        self,
        show: Show,
        update_at: datetime | None = None,
        *,
        force: bool = False,
    ) -> None:
        _cache = self._download_show_files_and_children(show, update_at)
        self._preload_show(show.id, preload_episodes=True).one()
        self.upsert_show(show.source, show.key, force=force)

    # TODO: Validate
    @override
    def update_show(self, show: Show, *, force: bool = False) -> None:
        logger.info("Updating show: {}", show.key)
        show = self._preload_show(
            show.key,
            source_key=show.source.key,
        ).one()
        self._preload_and_upsert_show(show, show.update_at, force=force)

    # TODO: Validate
    @override
    def update_season(self, season: Season) -> None:
        logger.info("Updating season: {}", season.key)
        season = self._preload_season(
            season.id,
            preload_show=True,
        ).one()
        self._download_season_files_and_children(season, update_at=season.update_at)
        self._preload_and_upsert_show(season.show)

    # TODO: Validate
    @override
    def update_episode(self, episode: Episode) -> None:
        logger.info("Updating episode: {}", episode.key)
        episode = self._preload_episode(episode.id, preload_source=True).one()
        self._download_episode_files(episode, update_at=episode.update_at)
        self._preload_and_upsert_show(episode.season.show)

    @override
    def on_update_plugin_failure(self, plugin: Plugin, error: Exception) -> None:
        plugin.update_at = tz_datetime.max()

    @override
    def on_update_source_failure(self, source: Source, error: Exception) -> None:
        source.update_at = tz_datetime.max()

    @override
    def on_update_show_failure(self, show: Show, error: Exception) -> None:
        show.update_at = tz_datetime.max()

    @override
    def on_update_season_failure(self, season: Season, error: Exception) -> None:
        season.update_at = tz_datetime.max()

    @override
    def on_update_episode_failure(self, episode: Episode, error: Exception) -> None:
        episode.update_at = tz_datetime.max()

    # TODO: Validate
    def _link_supplied_canonical_show(
        self,
        show: Show,
        canonical_show: Show | None,
    ) -> None:
        if canonical_show is None:
            return
        if not show.canonical_show_id:
            show.canonical_show = canonical_show
        link_canonical_show(self.session, show, canonical_show)

    # TODO: Validate
    def _link_supplied_canonical_shows(
        self,
        shows: Iterable[Show],
        canonical_show: Show | None,
    ) -> None:
        for show in shows:
            self._link_supplied_canonical_show(show, canonical_show)

    # TODO: Validate
    def _upsert_show_object(
        self,
        show: Show,
        source: Source,
        existing_show: Show | None,
        show_key: str,
    ) -> Show:
        """Store the website's own `Show` against the files it was read out of.

        A record being written again is built fresh off the website's files, so
        it knows nothing of the title the stored one is a copy of. That title is
        carried over rather than written away, since a listing is a copy of the
        same thing it was a copy of last time unless something works out
        otherwise, and what works it out runs after this. A title the `User`
        settled is kept whatever the new record says; otherwise a title the new
        record does name is the better answer and wins.
        """
        if existing_show and (
            existing_show.canonical_show_locked or not show.canonical_show_id
        ):
            show.canonical_show_id = existing_show.canonical_show_id
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
        """Store the website's own `Season` against the files it was read out of.

        The season the stored record is a copy of is carried over for the same
        reason the show's title is. No `User` ever settles a season by hand, so
        a new record naming one always wins.
        """
        if existing_season and not season.canonical_season_id:
            season.canonical_season_id = existing_season.canonical_season_id
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

        The episode the stored record is a copy of is carried over for the same
        reason the show's title is, and the note travels with it: how a link came
        to be made is most of what says whether it should be kept, so an episode
        that keeps its link keeps the reason for it too.
        """
        if existing_episode and (
            existing_episode.canonical_episode_locked
            or not episode.canonical_episode_id
        ):
            episode.canonical_episode_id = existing_episode.canonical_episode_id
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
    ) -> Show: ...

    # TODO: Validate
    def _upsert_source(self, *args: Any, **kwargs: Any) -> Source:  # noqa: ANN401 - Child signatures vary.
        """Create or update the plugin's `Source` record(s)."""
        msg = f"{self.plugin_key()} does not implement _upsert_source."
        raise NotImplementedError(msg)

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
        self.soft_delete_missing_seasons(show_key)
        for season_key in self._season_keys_from_file(show_key):
            self.soft_delete_missing_episodes(season_key, show_key)

    # TODO: Validate
    @classmethod
    @override
    def plugin_key(cls) -> str:
        return cls.__name__

    # TODO: Validate
    @classmethod
    def plugin_name(cls) -> str:
        """Return the name of the plugin."""
        return cls.__name__

    # TODO: Validate
    def _file[FileT: BaseFile[Any]](
        self,
        file_type: Callable[..., FileT],
        *identifiers: object,
    ) -> FileT:
        """Return the cached `file_type` instance for `identifiers`."""
        cache = (
            self._reusable_file_cache
            if file_type in self._PLUGIN_WIDE_FILES
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
    def raise_if_invalid_file(self, file: BaseFile[Any], url: str) -> None:
        file.download_if_outdated()
        if not file.database_record.content:
            msg = f"Invalid {self.plugin_key()} URL: {url}"
            raise InvalidURLError(msg)


# TODO: Validate
class URLHandlerPlugin[HandlerT: URLHandler[Any]](BasePlugin, ABC, register=False):
    _URL_HANDLERS: ClassVar[tuple[type[URLHandler[Any]], ...]]

    # TODO: Validate
    def get_url_handler(self, url: str) -> HandlerT:
        domain_regex = self._domain_regex()
        for handler_class in self._URL_HANDLERS:
            if match := re.match(handler_class._url_regex(domain_regex), url):
                return cast("HandlerT", handler_class(self, url, match.group(1)))  # type: ignore[call-arg]  # ty: ignore[too-many-positional-arguments]

        msg = f"Invalid {self.plugin_key()} URL: {url}"
        raise InvalidURLError(msg)

    # TODO: Validate
    @classmethod
    @override
    def url_regex(cls) -> str:
        domain_regex = cls._domain_regex()
        alternatives = "|".join(
            handler_class._url_regex(domain_regex)  # noqa: SLF001 - Same package.
            for handler_class in cls._URL_HANDLERS
        )
        return f"(?:{alternatives})"

    # TODO: Validate
    def _import_handler(
        self,
        handler: HandlerT,
        canonical_show: Show | None = None,
    ) -> list[URLImportResult]:
        """Setup then call upsert_show to import a new show.

        What a channel takes on from the import is returned rather than the show
        itself, since that is what a caller asking for a URL to be imported is
        asking for, and it is the handler that says what the URL named.
        """
        show_key = handler.show_key
        if show := self._preload_show(show_key).one_or_none():
            self._link_supplied_canonical_show(show, canonical_show)
            return handler.import_results(show)

        _cache = self._download_show_files_and_children(show_key)
        show = self.upsert_show(self.source, show_key, canonical_show=canonical_show)
        # After the reconcile `upsert_show` ends on rather than before it, since a
        # title nothing under the listing points at yet is one the reconcile would
        # take straight back off again.
        self._link_supplied_canonical_show(show, canonical_show)
        return handler.import_results(show)

    # TODO: Validate
    @override
    def import_url(
        self,
        url: str,
        canonical_show: Show | None = None,
    ) -> list[URLImportResult]:
        handler = self.get_url_handler(url)
        handler.raise_if_invalid()
        return self._import_handler(handler, canonical_show)


# `__init_subclass__` only runs for subclasses, so the entry points `BasePlugin`
# declares itself are wrapped here instead. Every other class, this file's
# `URLHandlerPlugin` included, is a subclass and is wrapped as it is declared.
BasePlugin._track_show_on_entry_points()  # noqa: SLF001 - Declared just above.
