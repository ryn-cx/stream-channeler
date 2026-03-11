# TODO: Validate
from abc import ABC, abstractmethod
from collections.abc import Callable
from functools import cache
from typing import Any, override

from sqlalchemy.orm import joinedload
from sqlmodel import Session

from app.episodes.models import Episode
from app.plugins.models import Plugin
from app.plugins.plugins.utils.abstract_plugin import AbstractPlugin, InvalidURLError
from app.plugins.plugins.utils.base_plugin.download import DownloadMixin
from app.plugins.plugins.utils.base_plugin.files import BaseFile
from app.plugins.plugins.utils.base_plugin.preload import PreloadMixin
from app.plugins.plugins.utils.base_plugin.timestamps import TimestampsMixin
from app.plugins.plugins.utils.base_plugin.url import URLMixin
from app.plugins.plugins.utils.base_plugin.watch import WatchMixin
from app.plugins.schemas import PluginInput
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from app.utils import tz_datetime


class BasePlugin(
    PreloadMixin,
    DownloadMixin,
    TimestampsMixin,
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
        self.__plugin_value: Plugin | None = None
        self.__preload_plugin()
        self.__upsert_plugin()

    def __preload_plugin(self) -> None:
        # assignment - The setter is designed to handle a Plugin or None value.
        self.plugin = Plugin.get(  # type: ignore[assignment]
            self.db,
            self.plugin_id(),
            # arg-type - joinedload always has type errors.
            options=[joinedload(Plugin.sources)],  # type: ignore[arg-type]
        )

    def __upsert_plugin(self) -> None:
        if self._has_plugin():
            if self.plugin.version != self._VERSION:
                msg = (
                    f"Plugin {self.plugin_id()!r} requires version {self._VERSION!r} "
                    f"but the database has version {self.plugin.version!r}. "
                    f"The database entry needs to be migrated."
                )
                raise RuntimeError(msg)

            if self.plugin.name != self._plugin_name():
                self.plugin.name = self._plugin_name()
                self.plugin.data_timestamp = tz_datetime.now()
            return

        self.plugin = PluginInput(
            key=self.plugin_id(),
            name=self._plugin_name(),
            version=self._VERSION,
            public=True,
            data_timestamp=tz_datetime.now(),
        ).upsert(self.db, None)

    # endregion

    # region Properties

    @property
    def plugin(self) -> Plugin:
        if not self.__plugin_value:
            msg = "Plugin has not been set yet."
            raise AttributeError(msg)

        return self.__plugin_value

    @plugin.setter
    def plugin(self, plugin: Plugin | None) -> None:
        if self.__plugin_value and not plugin:
            msg = "Plugin has already been set and cannot be set to None."
            raise AttributeError(msg)
        self.__plugin_value = plugin

    def _has_plugin(self) -> Plugin | None:
        return self.__plugin_value

    # endregion

    # region Update

    @override
    def update_show(self, show: Show) -> None:
        show = self._preload_show(show_key=show.key, preload_episodes=True).one()
        _cache = (self._download_show_files(show.key, show.update_at),)
        self._upsert_show(show.source, show_key=show.key)

    @override
    def update_season(self, season: Season) -> None:
        season = self._preload_season(
            season.id,
            preload_episodes=True,
            preload_show=True,
        ).one()
        _cache = (self._download_season_files(season.key, season.update_at),)
        self._upsert_season(season.show, season.key)

    @override
    def update_episode(self, episode: Episode) -> None:
        episode = self._preload_episode(
            episode.id,
            preload_season=True,
            preload_show=True,
        ).one()
        _cache = self._download_episode_files(episode.key, episode.update_at)
        self._upsert_episode(episode.season, episode.key)

    @abstractmethod
    def _upsert_show(
        self,
        source: Source,
        *,
        show_key: str = "",
        force_reimport: bool = False,
    ) -> None: ...

    @abstractmethod
    def _upsert_season(
        self,
        show: Show,
        season_key: str,
        *,
        force_reimport: bool = False,
    ) -> Season: ...

    @abstractmethod
    def _upsert_episode(
        self,
        season: Season,
        episode_key: str,
        *,
        force_reimport: bool = False,
    ) -> None: ...

    # endregion

    # region Other

    @classmethod
    @cache
    @override
    def plugin_id(cls) -> str:
        # TODO: Update name to ryn.cx to StreamChanneler.
        return f"ryn.cx-{cls._plugin_name()}"

    @classmethod
    @cache
    def _plugin_name(cls) -> str:
        """Returns the name of the plugin."""
        return cls.__name__

    def _get_cached_file[K, T](
        self,
        cache: dict[K, T],
        key: K,
        factory: Callable[[], T],
    ) -> T:
        """Generic helper to get or create cached file objects."""
        if key not in cache:
            cache[key] = factory()
        return cache[key]

    # TODO: Better name for this function?
    def raise_if_no_content(self, file: BaseFile[Any], url: str) -> None:
        """Validates that the URL content is valid for the plugin.

        Raises InvalidURLError if the URL content is not valid.

        This is used to detect failed downloads
        """
        if not file.get_content():
            msg = f"Invalid {self._plugin_name()} URL: {url}"
            raise InvalidURLError(msg)

    # endregion
