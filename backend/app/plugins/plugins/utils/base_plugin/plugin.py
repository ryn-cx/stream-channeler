# TODO: Validate
from abc import ABC, abstractmethod
from collections.abc import Callable
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
from app.users.service import get_or_create_plugin_user
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
        self.__upsert_plugin()

    def __upsert_plugin(self) -> None:
        plugin_user = get_or_create_plugin_user(session=self.db)
        existing = Plugin.get(
            self.db,
            self.plugin_id(),
            plugin_user,
            options=[joinedload(Plugin.sources)],  # type: ignore[arg-type]
        )

        if existing is None:
            self.plugin = PluginInput(
                key=self.plugin_id(),
                name=self._plugin_name(),
                version=self._VERSION,
                public=True,
                user_id=plugin_user.id,
                data_timestamp=tz_datetime.now(),
            ).upsert(plugin_user, None)
            return

        if existing.version != self._VERSION:
            msg = (
                f"Plugin {self.plugin_id()!r} requires version {self._VERSION!r} "
                f"but the database has version {existing.version!r}. "
                f"The database entry needs to be migrated."
            )
            raise RuntimeError(msg)

        if existing.name != self._plugin_name():
            existing.name = self._plugin_name()
            existing.data_timestamp = tz_datetime.now()
        if existing.user_id != plugin_user.id:
            existing.user_id = plugin_user.id
            existing.data_timestamp = tz_datetime.now()
        self.plugin = existing

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
        _cache = self._download_season_files(season.key, season.update_at)
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
    ) -> None: ...

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
    @override
    def plugin_id(cls) -> str:
        # TODO: Update name to ryn.cx to StreamChanneler.
        return f"{cls._plugin_name()}"

    @classmethod
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
