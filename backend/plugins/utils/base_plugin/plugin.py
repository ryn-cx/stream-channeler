# TODO: Validate
from abc import ABC, abstractmethod
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any, override

from loguru import logger
from sqlmodel import Session

from app.episodes.models import Episode
from app.models import BaseMediaMixin, Visibility
from app.plugins.models import Plugin
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from app.users.models import User
from app.users.service import get_or_create_plugin_user
from app.utils import tz_datetime
from plugins.utils.abstract_plugin import AbstractPlugin, InvalidURLError
from plugins.utils.base_plugin.files import BaseFile
from plugins.utils.base_plugin.preload import PreloadMixin
from plugins.utils.base_plugin.status import OutdatedMixin
from plugins.utils.base_plugin.url import URLMixin
from plugins.utils.base_plugin.watch import WatchMixin


class BasePlugin(
    PreloadMixin,
    OutdatedMixin,
    URLMixin,
    WatchMixin,
    AbstractPlugin,
    ABC,
    register=False,
):
    _VERSION: str

    @override
    def __init__(self, session: Session) -> None:
        self.session = session
        self._source: Source | None = None
        self._file_cache: dict[tuple[type, object], Any] = {}
        self._weakref_file_cache: dict[tuple[type, object], Any] = {}
        self.initialize_database()
        self._validate_plugin_version()

    @property
    def source(self) -> Source:
        """Return the plugin's `Source` record or raise if not initialized."""
        if self._source is None:
            msg = "Source has not been initialized."
            raise AttributeError(msg)
        return self._source

    @source.setter
    def source(self, value: Source) -> None:
        self._source = value

    @property
    def has_source(self) -> bool:
        """Return True if the plugin has a `Source` record."""
        return self._source is not None

    def initialize_database(self) -> None:
        """Create the `Plugin` and its `Source` record(s) and set instance attributes.

        Sets `self.plugin` if only a single `Plugin` record exists.
        Sets `self.source` if only a single `Source` record exists.
        """
        self.initialize_plugin()
        self.initialize_source()

    def initialize_plugin(self) -> None:
        """Create the `Plugin` record(s) and set `self.plugin`."""
        plugin_user = get_or_create_plugin_user(session=self.session)
        if existing_plugin := Plugin.get(self.session, plugin_user, self.plugin_key()):
            self.plugin = existing_plugin
        else:
            self.plugin = self._upsert_plugin(plugin_user, existing_plugin)

    def initialize_source(self) -> None:
        """Create the `Source` record(s) and set `self.source`."""
        if existing_source := Source.get(self.session, self.plugin, self.plugin_key()):
            self.source = existing_source
        else:
            self.source = self._upsert_source()

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
            visibility=Visibility.public,
            user_id=plugin_user.id,
        ).upsert(plugin_user, existing_plugin)

    @staticmethod
    def _existing_data_timestamp_or_now(record: BaseMediaMixin | None) -> datetime:
        """Return the record's data timestamp, or the current time if it has none."""
        if record and record.data_timestamp:
            return record.data_timestamp
        return tz_datetime.now()

    @staticmethod
    def _set_weekly_updates_from_episodes(
        show: Show,
        *,
        update_show: bool = True,
        update_seasons: bool = True,
    ) -> None:
        """Set update_at on the `Show`/`Season` based on `Episode.release_date`.

        `update_at` will be set to be a week after the latest `Episode.release_date` if
        that is a better `update_at` value than the current `update_at` value.
        """
        for season in show.active_children:
            for episode in season.active_children:
                if episode.release_date:
                    update_at = episode.release_date + timedelta(days=7)
                    if update_seasons:
                        season.set_update_at(update_at)
                    if update_show:
                        show.set_update_at(update_at)

    def _validate_plugin_version(self) -> None:
        if self.plugin.version != self._VERSION:
            msg = (
                f"Plugin {self.plugin_key()!r} requires version {self._VERSION!r} "
                f"but the database has version {self.plugin.version!r}. "
                f"The database record needs to be migrated."
            )
            raise RuntimeError(msg)

    def _cache_and_upsert_show(
        self,
        show: Show,
        update_at: datetime | None = None,
    ) -> None:
        _cache = self._download_show_files_and_children(show, update_at)
        self._preload_show(show.id, preload_episodes=True).one()
        self._upsert_show(show.source, show.key)

    @override
    def update_show(self, show: Show) -> None:
        logger.info("Updating show: {}", show.key)
        show = self._preload_show(
            show.key,
            source_key=show.source.key,
        ).one()
        self._cache_and_upsert_show(show, show.update_at)

    @override
    def update_season(self, season: Season) -> None:
        logger.info("Updating season: {}", season.key)
        season = self._preload_season(
            season.id,
            preload_show=True,
        ).one()
        self._download_season_files_and_children(season, update_at=season.update_at)
        self._cache_and_upsert_show(season.show)

    @override
    def update_episode(self, episode: Episode) -> None:
        logger.info("Updating episode: {}", episode.key)
        episode = self._preload_episode(episode.id, preload_source=True).one()
        self._download_episode_files(episode, update_at=episode.update_at)
        self._cache_and_upsert_show(episode.season.show)

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

    @abstractmethod
    def _upsert_show(
        self,
        source: Source,
        show_key: str,
    ) -> Show: ...

    def _upsert_source(self, *args: Any, **kwargs: Any) -> Source:  # noqa: ANN401 - Child signatures vary.
        """Create or update the plugin's `Source` record(s)."""
        msg = f"{self.plugin_key()} does not implement _upsert_source."
        raise NotImplementedError(msg)

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

    def soft_delete_missing_episodes(self, season_key: str) -> None:
        """Soft-delete episodes whose keys are not in the season's episode file."""
        episode_keys = self._episode_keys_from_file(season_key)
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

    @classmethod
    @override
    def plugin_key(cls) -> str:
        return cls.__name__

    @classmethod
    def plugin_name(cls) -> str:
        """Return the name of the plugin."""
        return cls.__name__

    def _get_cached_file[T](
        self,
        file_type: type[T],
        key: object,
        factory: Callable[[], T],
    ) -> T:
        cache_key = (file_type, key)
        if cached := self._weakref_file_cache.get(cache_key):
            return cached
        obj = factory()
        self._weakref_file_cache[cache_key] = obj
        return obj

    def _raise_if_no_content(self, file: BaseFile[Any], url: str) -> None:
        file.download_if_outdated()
        if not file.database_record.content:
            msg = f"Invalid {self.plugin_key()} URL: {url}"
            raise InvalidURLError(msg)
