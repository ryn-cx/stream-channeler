# TODO: Validate
from abc import abstractmethod
from collections.abc import Sequence
from datetime import datetime

from loguru import logger
from sqlmodel import Session

from app.plugins.models import File, Plugin
from app.plugins.plugins.utils.base_plugin.file_getters import FileGettersMixin
from app.shows.models import Show
from app.sources.models import Source


class DownloadMixin(FileGettersMixin):
    db: Session
    plugin: Plugin

    @classmethod
    @abstractmethod
    def _plugin_name(cls) -> str: ...

    def _pretty_show_name(self, show_key: str) -> str:
        """Get a pretty name for the show if available."""
        if (
            source := Source.get_from_memory(self.db, self.plugin, self._plugin_name())
        ) and (show := Show.get_from_memory(self.db, source, show_key)):
            return show.name or show_key
        return show_key

    def _download_initial_files(self, show_key: str) -> list[File]:
        logger.info(f"Downloading All Files For: {self._pretty_show_name(show_key)}")
        return self._download_show_files(show_key)

    def _download_show_files(
        self,
        show_key: str,
        update_at: datetime | None = None,
        preloaded_show_files: Sequence[File] | None = None,
        *,
        skip_seasons: bool = False,
        skip_episodes: bool = False,
    ) -> list[File]:
        if not preloaded_show_files:
            preloaded_show_files = self._preload_show_files(show_key)
        show_files = self._show_files(show_key)
        for show_file in show_files:
            show_file.download_if_outdated(update_at)
        all_files = [file.database_entry for file in show_files]
        if not skip_seasons:
            all_files.extend(self._download_all_season_files(show_key))
        if not skip_episodes:
            all_files.extend(self._download_all_episode_files(show_key))
        return all_files

    def _download_season_files(
        self,
        season_key: str,
        update_at: datetime | None = None,
        preloaded_season_files: Sequence[File] | None = None,
        *,
        skip_episodes: bool = False,
    ) -> list[File]:
        if not preloaded_season_files:
            preloaded_season_files = self._preload_season_files([season_key])
        season_files = self._season_files(season_key)
        for season_file in season_files:
            season_file.download_if_outdated(update_at)
        all_files = [file.database_entry for file in season_files]
        if not skip_episodes:
            all_files.extend(self._download_season_episode_files(season_key))
        return all_files

    def _download_season_episode_files(self, season_key: str) -> list[File]:
        video_keys = self._video_keys_from_file(season_key)
        episode_cache = self._preload_episode_files(list(video_keys))
        all_files: list[File] = []
        for episode_key in video_keys:
            all_files.extend(
                self._download_episode_files(
                    episode_key,
                    preloaded_episode_files=episode_cache,
                ),
            )
        return all_files

    def _download_episode_files(
        self,
        episode_key: str,
        update_at: datetime | None = None,
        preloaded_episode_files: Sequence[File] | None = None,
    ) -> list[File]:
        if not preloaded_episode_files:
            preloaded_episode_files = self._preload_episode_files([episode_key])
        episode_files = self._episode_files(episode_key)
        for episode_file in episode_files:
            episode_file.download_if_outdated(update_at)
        return [file.database_entry for file in episode_files]

    def _download_all_season_files(self, show_key: str) -> list[File]:
        season_keys = self._season_keys_from_file(show_key)
        season_cache = self._preload_season_files(season_keys)
        all_files: list[File] = []
        for season_key in season_keys:
            all_files.extend(
                self._download_season_files(
                    season_key,
                    preloaded_season_files=season_cache,
                    skip_episodes=True,
                ),
            )
        return all_files

    def _download_all_episode_files(self, show_key: str) -> list[File]:
        season_keys = self._season_keys_from_file(show_key)
        all_files: list[File] = []
        for season_key in season_keys:
            all_files.extend(self._download_season_episode_files(season_key))
        return all_files

    @abstractmethod
    def _preload_show_files(self, show_key: str) -> Sequence[File]: ...

    @abstractmethod
    def _preload_season_files(self, season_keys: list[str]) -> Sequence[File]: ...

    @abstractmethod
    def _preload_episode_files(self, episode_keys: list[str]) -> Sequence[File]: ...

    @abstractmethod
    def _season_keys_from_file(self, show_key: str) -> list[str]: ...

    @abstractmethod
    def _video_keys_from_file(
        self,
        season_keys: str | list[str],
    ) -> list[str]: ...
