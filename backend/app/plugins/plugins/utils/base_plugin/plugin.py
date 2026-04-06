# TODO: Validate
from abc import ABC, abstractmethod
from collections.abc import Callable
from datetime import datetime
from typing import Any, TypeIs, override
from weakref import WeakValueDictionary

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
    def __init__(
        self,
        db: Session,
        *,
        url: str | None = None,
        source: Source | None = None,
        show: Show | None = None,
        season: Season | None = None,
        episode: Episode | None = None,
    ) -> None:
        self.db = db
        self._file_cache: dict[tuple[type, object], Any] = {}
        self._weakref_file_cache: WeakValueDictionary[tuple[type, object], Any] = (
            WeakValueDictionary()
        )
        self.initialize_plugin()
        self._validate_plugin_version()

    @override
    def initialize_plugin(self) -> None:
        plugin_user = get_or_create_plugin_user(session=self.db)
        existing = Plugin.get(
            self.db,
            self.plugin_key(),
            plugin_user,
            options=[joinedload(Plugin.sources)],  # type: ignore[arg-type]
        )

        if not existing:
            self.plugin = Plugin(
                key=self.plugin_key(),
                name=self.plugin_key(),
                version=self._VERSION,
                public=True,
                user_id=plugin_user.id,
            ).upsert(plugin_user, existing)
        else:
            self.plugin = existing

    def _validate_plugin_version(self) -> None:
        if self.plugin.version != self._VERSION:
            msg = (
                f"Plugin {self.plugin_key()!r} requires version {self._VERSION!r} "
                f"but the database has version {self.plugin.version!r}. "
                f"The database entry needs to be migrated."
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
            preload_episodes=True,
        ).one()
        _cache = self._download_show_files(show.key, show.update_at)
        self._upsert_show(show.source, show.key)

    @override
    def update_season(self, season: Season) -> None:
        logger.info("Updating season: {}", season.key)
        season = self._preload_season(
            season.id,
            preload_episodes=True,
            preload_show=True,
        ).one()
        self._download_season_files(
            season.key,
            season.update_at,
            show_key=season.show.key,
        )
        _cache = self._download_show_files(season.show.key)
        self._upsert_show(season.show.source, season.show.key)

    @override
    def update_episode(self, episode: Episode) -> None:
        logger.info("Updating episode: {}", episode.key)
        episode = self._preload_episode(episode.id, preload_source=True).one()
        self._download_episode_files(
            episode.key,
            episode.update_at,
            season_key=episode.season.key,
            show_key=episode.season.show.key,
        )
        _cache = self._download_show_files(episode.season.show.key)
        self._upsert_show(episode.season.show.source, episode.season.show.key)

    @abstractmethod
    def _upsert_show(
        self,
        source: Source,
        show_key: str,
        *,
        force_reimport: bool = False,
    ) -> Show: ...

    # endregion

    @staticmethod
    def _is_up_to_date(
        entity: Show | Season | Episode | None,
        timestamp: datetime,
    ) -> TypeIs[Show | Season | Episode]:
        """Check if an entity exists and is up to date.

        When this returns True, the type checker narrows entity to not-None.
        """
        return entity is not None and entity.data_timestamp == timestamp

    @classmethod
    @override
    def plugin_key(cls) -> str:
        return cls.__name__

    def _get_weakref_cached_file[T](
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
        if not file.database_entry.content:
            msg = f"Invalid {self.plugin_key()} URL: {url}"
            raise InvalidURLError(msg)
