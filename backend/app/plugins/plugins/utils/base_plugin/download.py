# TODO: Validate
from abc import abstractmethod
from collections.abc import Sequence
from datetime import datetime

from sqlmodel import Session, col, select

from app.plugins.models import File, Plugin
from app.plugins.plugins.utils.abstract_plugin import AbstractPlugin
from app.plugins.plugins.utils.base_plugin.file_getters import FileGettersMixin
from app.shows.models import Show
from app.sources.models import Source


class DownloadMixin(FileGettersMixin, AbstractPlugin, register=False):
    db: Session
    plugin: Plugin
    _skip_downloading_seasons: bool = False
    _skip_downloading_episodes: bool = False

    def _pretty_show_name(self, show_key: str) -> str:
        """Get a pretty name for the show if available."""
        if (
            source := Source.get_from_memory(self.db, self.plugin, self.plugin_key())
        ) and (show := Show.get_from_memory(self.db, source, show_key)):
            return show.name or show_key
        return show_key

    def _download_show_files(
        self,
        show_key: str,
        update_at: datetime | None = None,
        preloaded_show_files: Sequence[File] | None = None,
        *,
        skip_seasons: bool | None = None,
        skip_episodes: bool | None = None,
    ) -> list[File]:
        if skip_seasons is None:
            skip_seasons = self._skip_downloading_seasons
        if skip_episodes is None:
            skip_episodes = self._skip_downloading_episodes
        if not preloaded_show_files:
            preloaded_show_files = self._preload_show_files(show_key)
        show_files = self._show_files(show_key=show_key)
        for show_file in show_files:
            show_file.download_if_outdated(update_at)
        all_files = [file.database_entry for file in show_files]
        if not skip_seasons:
            all_files.extend(
                self._download_all_season_files(show_key, skip_episodes=skip_episodes),
            )
        return all_files

    def _download_season_files(
        self,
        season_key: str,
        update_at: datetime | None = None,
        preloaded_season_files: Sequence[File] | None = None,
        *,
        show_key: str | None = None,
        skip_episodes: bool | None = None,
    ) -> list[File]:
        if skip_episodes is None:
            skip_episodes = self._skip_downloading_episodes
        if not preloaded_season_files:
            preloaded_season_files = self._preload_season_files(
                [season_key],
                show_key=show_key,
            )
        season_files = self._season_files(season_key=season_key, show_key=show_key)
        for season_file in season_files:
            season_file.download_if_outdated(update_at)
        all_files = [file.database_entry for file in season_files]
        if not skip_episodes:
            all_files.extend(
                self._download_all_episode_files(
                    season_key,
                    show_key=show_key,
                ),
            )
        return all_files

    def _download_episode_files(
        self,
        episode_key: str,
        update_at: datetime | None = None,
        preloaded_episode_files: Sequence[File] | None = None,
        *,
        season_key: str | None = None,
        show_key: str | None = None,
    ) -> list[File]:
        if not preloaded_episode_files:
            preloaded_episode_files = self._preload_episode_files(
                [episode_key],
                season_key=season_key,
                show_key=show_key,
            )
        episode_files = self._episode_files(
            episode_key=episode_key,
            season_key=season_key,
            show_key=show_key,
        )
        for episode_file in episode_files:
            episode_file.download_if_outdated(update_at)
        return [file.database_entry for file in episode_files]

    def _download_all_season_files(
        self,
        show_key: str,
        *,
        skip_episodes: bool | None = None,
    ) -> list[File]:
        if skip_episodes is None:
            skip_episodes = self._skip_downloading_episodes
        season_keys = self._season_keys_from_file(show_key)
        season_cache = self._preload_season_files(season_keys, show_key=show_key)
        all_files: list[File] = []
        for season_key in season_keys:
            all_files.extend(
                self._download_season_files(
                    season_key,
                    preloaded_season_files=season_cache,
                    show_key=show_key,
                    skip_episodes=True,
                ),
            )
        if not skip_episodes:
            all_episode_file_keys = [
                file.file_key()
                for season_key in season_keys
                for episode_key in self._episode_keys_from_file(season_key)
                for file in self._episode_files(
                    episode_key=episode_key,
                    season_key=season_key,
                    show_key=show_key,
                )
            ]
            episode_cache = self._get_files_by_keys(all_episode_file_keys)
            for season_key in season_keys:
                all_files.extend(
                    self._download_all_episode_files(
                        season_key,
                        show_key=show_key,
                        preloaded_episode_files=episode_cache,
                    ),
                )
        return all_files

    def _download_all_episode_files(
        self,
        season_key: str,
        *,
        show_key: str | None = None,
        preloaded_episode_files: Sequence[File] | None = None,
    ) -> list[File]:
        video_keys = self._episode_keys_from_file(season_key)
        if not preloaded_episode_files:
            preloaded_episode_files = self._preload_episode_files(
                video_keys,
                season_key=season_key,
                show_key=show_key,
            )
        all_files: list[File] = []
        for episode_key in video_keys:
            all_files.extend(
                self._download_episode_files(
                    episode_key,
                    preloaded_episode_files=preloaded_episode_files,
                    season_key=season_key,
                    show_key=show_key,
                ),
            )
        return all_files

    # region Preload

    def _get_files_by_keys(self, file_keys: list[str]) -> Sequence[File]:
        if not file_keys:
            return []
        statement = (
            select(File)
            .where(File.plugin == self.plugin)
            .where(col(File.key).in_(file_keys))
        )
        return self.db.exec(statement).all()

    def _preload_show_files(self, show_key: str) -> Sequence[File]:
        file_keys = [file.file_key() for file in self._show_files(show_key=show_key)]
        return self._get_files_by_keys(file_keys)

    def _preload_season_files(
        self,
        season_keys: list[str],
        *,
        show_key: str | None = None,
    ) -> Sequence[File]:
        file_keys = [
            file.file_key()
            for season_key in season_keys
            for file in self._season_files(season_key=season_key, show_key=show_key)
        ]
        return self._get_files_by_keys(file_keys)

    def _preload_episode_files(
        self,
        episode_keys: list[str],
        *,
        season_key: str | None = None,
        show_key: str | None = None,
    ) -> Sequence[File]:
        file_keys = [
            file.file_key()
            for episode_key in episode_keys
            for file in self._episode_files(
                episode_key=episode_key,
                season_key=season_key,
                show_key=show_key,
            )
        ]
        return self._get_files_by_keys(file_keys)

    # endregion Preload

    @abstractmethod
    def _season_keys_from_file(self, show_key: str) -> list[str]: ...

    @abstractmethod
    def _episode_keys_from_file(self, season_keys: str | list[str]) -> list[str]: ...
