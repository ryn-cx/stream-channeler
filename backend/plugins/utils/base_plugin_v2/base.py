# TODO: Validate
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, ClassVar, Self, override

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
    InvalidURLError,
    URLImportResult,
)
from plugins.utils.base_plugin_v2.files import INITIAL_FILE_IDENTIFIER, BaseFile
from plugins.utils.base_plugin_v2.outdated_check import OutdatedCheckMixin
from plugins.utils.base_plugin_v2.preload import PreloadMixin
from plugins.utils.base_plugin_v2.url import URLMixin

if TYPE_CHECKING:
    from plugins.utils.base_plugin_v2.initialize import PluginInitializer
    from plugins.utils.base_plugin_v2.workers import (
        Updater,
        URLImporter,
    )

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
class PluginBase(PreloadMixin, OutdatedCheckMixin, URLMixin, ABC):
    session: Session
    plugin: Plugin
    _sources: dict[str, Source]
    _file_cache: dict[object, Any]
    initializer: ClassVar[type[PluginInitializer]]
    url_importer: ClassVar[type[URLImporter]]
    updater: ClassVar[type[Updater]]

    def __init__(self, session: Session) -> None:
        self.session = session
        self._file_cache = {}
        self.plugin = Plugin.get_one(session, self.plugin_name())
        self._sources = {source.key: source for source in self.plugin.sources}

    @classmethod
    @abstractmethod
    def plugin_name(cls) -> str: ...

    @classmethod
    @abstractmethod
    def favicon_url(cls) -> str | None: ...

    @classmethod
    def name_on_tmdb(cls) -> tuple[str, ...]:
        return (cls.plugin_name(),)

    @classmethod
    def _source_keys(cls) -> tuple[str, ...]:
        return (cls.plugin_name(),)

    @classmethod
    def matches_tmdb_provider(cls, provider_name: str) -> bool:
        return provider_name in cls.name_on_tmdb()

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
    @classmethod
    def _upsert_source(
        cls,
        session: Session,
        plugin: Plugin,
        source_key: str,
    ) -> Source:
        """Create or update the plugin's `Source` record(s)."""
        msg = f"{cls.plugin_name()} does not implement _upsert_source."
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
        _cache = self._preload_show(show_key, preload_episodes=True).all()
        self.soft_delete_missing_seasons(show_key)
        for season_key in self._season_keys_from_file(show_key):
            self.soft_delete_missing_episodes(season_key, show_key)

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
        if cached := self._file_cache.get(cache_key):
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
    @classmethod
    def initialize_db(cls, session: Session) -> None:
        cls.initializer.initialize_db(session)

    # TODO: Validate
    @classmethod
    def url_regex(cls) -> str:
        return cls.url_importer.url_regex()

    # TODO: Validate
    def import_url(
        self,
        url: str,
        canonical_show: Show | None = None,
        *,
        force: bool = False,
    ) -> list[URLImportResult]:
        return self.url_importer(self, url).import_url(canonical_show, force=force)

    # TODO: Validate
    def update_show(self, show: Show, *, force: bool = False) -> None:
        self.updater(self, show).update(force=force)

    # TODO: Validate
    def update_season(self, season: Season) -> None:
        self.updater(self, season).update()

    # TODO: Validate
    def update_episode(self, episode: Episode) -> None:
        self.updater(self, episode).update()

    # TODO: Validate
    def on_update_show_failure(self, show: Show, error: Exception) -> None:
        self.updater(self, show).on_failure(error)

    # TODO: Validate
    def on_update_season_failure(self, season: Season, error: Exception) -> None:
        self.updater(self, season).on_failure(error)

    # TODO: Validate
    def on_update_episode_failure(self, episode: Episode, error: Exception) -> None:
        self.updater(self, episode).on_failure(error)

    # TODO: Validate
    def raise_if_invalid_file(self, file: BaseFile[Any], url: str) -> None:
        file.download_if_outdated()
        if not file.database_record.content:
            msg = f"Invalid {self.plugin_name()} URL: {url}"
            raise InvalidURLError(msg)


# TODO: Validate
class ReadURLBase(PluginBase, ABC):
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
    def _import_results(self, show: Show) -> list[URLImportResult]:
        results = [URLImportResult.show_import_results(show)]
        results += [
            URLImportResult.show_import_results(canonical_show)
            for canonical_show in show.canonical_shows
        ]
        return results
