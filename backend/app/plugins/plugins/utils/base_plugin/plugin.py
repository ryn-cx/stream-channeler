# TODO: Validate
from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any, override

from loguru import logger
from sqlalchemy.orm import joinedload
from sqlmodel import Session

from app.episodes.models import Episode
from app.plugins.models import Plugin
from app.plugins.plugins.utils.abstract_plugin import AbstractPlugin, InvalidURLError
from app.plugins.plugins.utils.base_plugin.download import DownloadMixin
from app.plugins.plugins.utils.base_plugin.files import BaseFile
from app.plugins.plugins.utils.base_plugin.preload import PreloadMixin
from app.plugins.plugins.utils.base_plugin.url import URLMixin
from app.plugins.plugins.utils.base_plugin.watch import WatchMixin
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from app.users.service import get_or_create_plugin_user


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

    # region Initialization

    @override
    def __init__(self, session: Session) -> None:
        self.session = session
        self._file_cache: dict[tuple[type, object], Any] = {}
        self._weakref_file_cache: dict[tuple[type, object], Any] = {}
        self.initialize_database()
        self._validate_plugin_version()

    def initialize_database(self) -> None:
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
                public=True,
                user_id=plugin_user.id,
            ).upsert(plugin_user, existing_plugin)
        else:
            self.plugin = existing_plugin

    def _validate_plugin_version(self) -> None:
        if self.plugin.version != self._VERSION:
            msg = (
                f"Plugin {self.plugin_key()!r} requires version {self._VERSION!r} "
                f"but the database has version {self.plugin.version!r}. "
                f"The database record needs to be migrated."
            )
            raise RuntimeError(msg)

    # endregion

    # region Update

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

    # endregion

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
