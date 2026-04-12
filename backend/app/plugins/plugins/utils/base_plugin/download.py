# TODO: Validate
from abc import ABC, abstractmethod
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlmodel import col, select

from app.plugins.models import File
from app.plugins.plugins.utils.base_plugin.files import BaseFile


class DownloadMixin(ABC):
    # region File Groups

    @abstractmethod
    def _show_files(self, show_key: str) -> Sequence[BaseFile[Any]]:
        """Return the files associated with the show."""

    @abstractmethod
    def _season_files(
        self,
        season_key: str,
        show_key: str,
    ) -> Sequence[BaseFile[Any]]:
        """Return the files associated with the season."""

    @abstractmethod
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        show_key: str,
    ) -> Sequence[BaseFile[Any]]:
        """Return the files associated with the episode."""

    # endregion File Groups

    # region Data timestamps

    @staticmethod
    def _file_timestamp(files: Sequence[BaseFile[Any]]) -> datetime:
        """Get the timestamp of the first file in the sequence."""
        return files[0].database_record.data_timestamp

    def show_data_timestamp(self, show_key: str) -> datetime:
        """Return the data timestamp for the show's files."""
        return self._file_timestamp(self._show_files(show_key))

    def season_data_timestamp(self, season_key: str, show_key: str) -> datetime:
        """Return the data timestamp for the season's files."""
        return self._file_timestamp(self._season_files(season_key, show_key))

    def episode_data_timestamp(
        self,
        episode_key: str,
        season_key: str,
        show_key: str,
    ) -> datetime:
        """Return the data timestamp for the episode's files."""
        return self._file_timestamp(
            self._episode_files(episode_key, season_key, show_key),
        )

    # endregion Data timestamps

    # region Download

    def _download_show_files(
        self,
        show_key: str,
        update_at: datetime | None = None,
        preloaded_show_files: Sequence[File] | None = None,
    ) -> list[File]:
        if not preloaded_show_files:
            preloaded_show_files = self._preload_show_files(show_key)
        show_files = self._show_files(show_key)
        for show_file in show_files:
            show_file.download_if_outdated(update_at)
        all_files = [file.database_record for file in show_files]
        all_files.extend(self._download_all_season_files(show_key))
        return all_files

    def _download_all_season_files(
        self,
        show_key: str,
        preloaded_seasons_files: Sequence[File] | None = None,
    ) -> list[File]:
        season_keys = self._season_keys_from_file(show_key)
        if not preloaded_seasons_files:
            preloaded_seasons_files = self._preload_season_files(
                season_keys,
                show_key,
            )
        all_files: list[File] = []
        for season_key in season_keys:
            season_files = self._season_files(season_key, show_key)
            for season_file in season_files:
                season_file.download_if_outdated()
            all_files.extend(file.database_record for file in season_files)

        all_episode_file_keys = [
            file.file_key()
            for season_key in season_keys
            for episode_key in self._episode_keys_from_file(season_key)
            for file in self._episode_files(episode_key, season_key, show_key)
        ]
        preloaded_episodes_files = self._get_files_by_keys(all_episode_file_keys)
        for season_key in season_keys:
            all_files.extend(
                self._download_all_episode_files(
                    season_key,
                    show_key,
                    preloaded_episodes_files,
                ),
            )
        return all_files

    def _download_all_episode_files(
        self,
        season_key: str,
        show_key: str,
        preloaded_episodes_files: Sequence[File] | None = None,
    ) -> list[File]:
        video_keys = self._episode_keys_from_file(season_key)
        if not preloaded_episodes_files:
            preloaded_episodes_files = self._preload_episode_files(
                video_keys,
                season_key,
                show_key,
            )
        all_files: list[File] = []
        for episode_key in video_keys:
            all_files.extend(
                self._download_episode_files(
                    episode_key,
                    season_key,
                    show_key,
                    preloaded_episode_files=preloaded_episodes_files,
                ),
            )
        return all_files

    def _download_season_files(
        self,
        season_key: str,
        show_key: str,
        update_at: datetime | None = None,
        preloaded_season_files: Sequence[File] | None = None,
    ) -> list[File]:
        if not preloaded_season_files:
            preloaded_season_files = self._preload_season_files(
                [season_key],
                show_key,
            )
        season_files = self._season_files(season_key, show_key)
        for season_file in season_files:
            season_file.download_if_outdated(update_at)
        all_files = [file.database_record for file in season_files]
        all_files.extend(self._download_all_episode_files(season_key, show_key))
        return all_files

    def _download_episode_files(
        self,
        episode_key: str,
        season_key: str,
        show_key: str,
        update_at: datetime | None = None,
        preloaded_episode_files: Sequence[File] | None = None,
    ) -> list[File]:
        if not preloaded_episode_files:
            preloaded_episode_files = self._preload_episode_files(
                [episode_key],
                season_key,
                show_key,
            )
        episode_files = self._episode_files(episode_key, season_key, show_key)
        for episode_file in episode_files:
            episode_file.download_if_outdated(update_at)
        return [file.database_record for file in episode_files]

    # endregion Download

    # region Preload

    def _get_files_by_keys(self, file_keys: list[str]) -> Sequence[File]:
        if not file_keys:
            return []
        # TODO: Fix these type errors
        statement = (
            select(File)
            .where(File.plugin == self.plugin)
            .where(col(File.key).in_(file_keys))
        )
        return self.db.exec(statement).all()

    def _preload_show_files(self, show_key: str) -> Sequence[File]:
        file_keys = [file.file_key() for file in self._show_files(show_key)]
        return self._get_files_by_keys(file_keys)

    def _preload_season_files(
        self,
        season_keys: list[str],
        show_key: str,
    ) -> Sequence[File]:
        file_keys = [
            file.file_key()
            for season_key in season_keys
            for file in self._season_files(season_key, show_key)
        ]
        return self._get_files_by_keys(file_keys)

    def _preload_episode_files(
        self,
        episode_keys: list[str],
        season_key: str,
        show_key: str,
    ) -> Sequence[File]:
        file_keys = [
            file.file_key()
            for episode_key in episode_keys
            for file in self._episode_files(episode_key, season_key, show_key)
        ]
        return self._get_files_by_keys(file_keys)

    # endregion Preload

    @abstractmethod
    def _season_keys_from_file(self, show_key: str) -> list[str]: ...

    @abstractmethod
    def _episode_keys_from_file(self, season_keys: str | list[str]) -> list[str]: ...
