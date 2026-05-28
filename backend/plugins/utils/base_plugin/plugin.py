# TODO: Validate
from abc import ABC, abstractmethod
from collections.abc import Callable
from datetime import timedelta
from typing import Any, override

from loguru import logger
from sqlalchemy.orm import joinedload
from sqlmodel import Session

from app.episodes.models import Episode
from app.models import Visibility
from app.plugins.models import Plugin
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from app.users.service import get_or_create_plugin_user
from plugins.utils.abstract_plugin import AbstractPlugin, InvalidURLError
from plugins.utils.base_plugin.download import DownloadMixin
from plugins.utils.base_plugin.files import BaseFile
from plugins.utils.base_plugin.preload import PreloadMixin
from plugins.utils.base_plugin.url import URLMixin
from plugins.utils.base_plugin.watch import WatchMixin


class BasePlugin(
    PreloadMixin,
    DownloadMixin,
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
        if self._source is None:
            msg = "Source has not been initialized."
            raise AttributeError(msg)
        return self._source

    @source.setter
    def source(self, value: Source) -> None:
        self._source = value

    @property
    def has_source(self) -> bool:
        return self._source is not None

    def initialize_database(self) -> None:
        """Add the `Plugin (class)` to the database if it doesn't already exist.

        This will always set `self.plugin` to the database record for the `Plugin`, and
        if there is only one `Source` for the plugin, it will set `self.source` to that
        source.
        """
        plugin_user = get_or_create_plugin_user(session=self.session)
        existing_plugin = Plugin.get(
            self.session,
            plugin_user,
            self.plugin_key(),
            options=[joinedload(Plugin.sources)],  # type: ignore[arg-type]
        )

        if not existing_plugin:
            self.plugin = Plugin(
                key=self.plugin_key(),
                name=self.plugin_key(),
                version=self._VERSION,
                visibility=Visibility.public,
                user_id=plugin_user.id,
            ).upsert(plugin_user, existing_plugin)
        else:
            self.plugin = existing_plugin
            if len(self.plugin.sources) == 1:
                self._source = self.plugin.sources[0]

        self.initialize_source()

    def initialize_source(self) -> None:
        """Hook for plugins to set up their source(s) after the plugin record exists."""

    @staticmethod
    def _set_weekly_updates_from_episodes(
        show: Show,
        *,
        update_show: bool = True,
        update_seasons: bool = True,
    ) -> None:
        """Set update_at on the show and/or seasons from episode release dates.

        Each episode's release_date + 7 days is offered to `set_update_at`
        so the entity is re-checked roughly one week after the episode aired.
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

    @override
    def update_show(self, show: Show) -> None:
        logger.info("Updating show: {}", show.key)
        show = self._preload_show(
            show_key=show.key,
            source_key=show.source.key,
        ).one()
        _cache = self._download_show_files(show.key, show.update_at)
        show = self._preload_show(
            show_key=show.key,
            source_key=show.source.key,
            preload_episodes=True,
        ).one()
        self._upsert_show(show.source, show.key)

    @override
    def update_season(self, season: Season) -> None:
        logger.info("Updating season: {}", season.key)
        season = self._preload_season(
            season.id,
            preload_episodes=True,
            preload_show=True,
        ).one()
        self._download_season_files(season.key, season.show.key, season.update_at)
        _cache = self._download_show_files(season.show.key)
        self._preload_show(show_id=season.show.id, preload_episodes=True).one()
        self._upsert_show(season.show.source, season.show.key)

    @override
    def update_episode(self, episode: Episode) -> None:
        logger.info("Updating episode: {}", episode.key)
        episode = self._preload_episode(episode.id, preload_source=True).one()
        self._download_episode_files(
            episode.key,
            episode.season.key,
            episode.season.show.key,
            episode.update_at,
        )
        _cache = self._download_show_files(episode.season.show.key)
        self._preload_show(
            show_id=episode.season.show.id,
            preload_episodes=True,
        ).one()
        self._upsert_show(episode.season.show.source, episode.season.show.key)

    @abstractmethod
    def _upsert_show(
        self,
        source: Source,
        show_key: str,
    ) -> Show: ...

    def soft_delete_missing_seasons(self, show_key: str) -> None:
        """Soft-delete seasons whose keys are not in the show's season file."""
        expected_keys = self._season_keys_from_file(show_key)
        source_ids = {source.id for source in self.plugin.sources}
        for obj in list(self.session.identity_map.values()):
            if (
                isinstance(obj, Show)
                and obj.key == show_key
                and obj.source_id in source_ids
            ):
                obj.soft_delete_missing_children(expected_keys)

    def soft_delete_missing_episodes(self, season_key: str) -> None:
        """Soft-delete episodes whose keys are not in the season's episode file."""
        expected_keys = self._episode_keys_from_file(season_key)
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
                obj.soft_delete_missing_children(expected_keys)

    @classmethod
    @override
    def plugin_key(cls) -> str:
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

    def raise_invalid_url_if_no_content(self, file: BaseFile[Any], url: str) -> None:
        if not file.database_record.content:
            msg = f"Invalid {self.plugin_key()} URL: {url}"
            raise InvalidURLError(msg)
