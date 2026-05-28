# TODO: Validate
from abc import ABC, abstractmethod
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlmodel import Session, col, select

from app.plugins.models import File
from plugins.utils.base_plugin.files import BaseFile


class DownloadMixin(ABC):
    session: Session

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

    def _plugin_files(self) -> Sequence[BaseFile[Any]]:
        """Return the files associated with the plugin."""
        raise NotImplementedError("This plugin does not have plugin specific files.")

    @staticmethod
    def _file_timestamp(files: Sequence[BaseFile[Any]]) -> datetime:
        """Get the timestamp of the first file in the sequence."""
        return files[0].data_timestamp

    def plugin_data_timestamp(self) -> datetime:
        """Return the data timestamp for the plugin's files."""
        return self._file_timestamp(self._plugin_files())

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

    @staticmethod
    def _download_outdated_files(
        files: Sequence[BaseFile[Any]],
        update_at: datetime | None = None,
    ) -> list[File]:
        for file in files:
            file.download_if_outdated(update_at)
        return [file.database_record for file in files]

    def _download_show_files(
        self,
        show_key: str,
        update_at: datetime | None = None,
    ) -> list[File]:
        try:
            _cache = self._preload_show_files(show_key)
            show_files = self._show_files(show_key)
            all_files = self._download_outdated_files(show_files, update_at)
            all_files.extend(self._download_all_season_files(show_key))
            return all_files
        finally:
            self.session.commit()

    def _download_season_files(
        self,
        season_key: str,
        show_key: str,
        update_at: datetime | None = None,
    ) -> list[File]:
        try:
            _cache = self._preload_season_files([season_key], show_key)
            season_files = self._season_files(season_key, show_key)
            all_files = self._download_outdated_files(season_files, update_at)
            all_files.extend(self._download_all_episode_files(season_key, show_key))
            return all_files
        finally:
            self.session.commit()

    def _download_episode_files(
        self,
        episode_key: str,
        season_key: str,
        show_key: str,
        update_at: datetime | None = None,
    ) -> list[File]:
        try:
            _cache = self._preload_episode_files([episode_key], season_key, show_key)
            episode_files = self._episode_files(episode_key, season_key, show_key)
            return self._download_outdated_files(episode_files, update_at)
        finally:
            self.session.commit()

    def _download_all_season_files(
        self,
        show_key: str,
    ) -> list[File]:
        season_keys = self._season_keys_from_file(show_key)
        _cache = self._preload_season_files(season_keys, show_key)
        all_files: list[File] = []
        for season_key in season_keys:
            season_files = self._season_files(season_key, show_key)
            all_files.extend(self._download_outdated_files(season_files))
        _episode_cache = self._preload_all_episode_files(season_keys, show_key)
        for season_key in season_keys:
            all_files.extend(self._download_all_episode_files(season_key, show_key))
        return all_files

    def _download_all_episode_files(
        self,
        season_key: str,
        show_key: str,
    ) -> list[File]:
        video_keys = self._episode_keys_from_file(season_key)
        _cache = self._preload_episode_files(video_keys, season_key, show_key)
        all_files: list[File] = []
        for episode_key in video_keys:
            episode_files = self._episode_files(episode_key, season_key, show_key)
            all_files.extend(self._download_outdated_files(episode_files))
        return all_files

    def _get_files_by_keys(self, file_keys: list[str]) -> Sequence[File]:
        if not file_keys:
            return []
        # TODO: Fix these type errors
        statement = (
            select(File)
            .where(File.plugin == self.plugin)  # type: ignore[attr-defined]
            .where(col(File.key).in_(file_keys))
        )
        return self.session.exec(statement).all()

    def _preload_show_files(
        self,
        show_key: str,
        preloaded_files: Sequence[File] | None = None,
    ) -> Sequence[File]:
        if preloaded_files:
            return preloaded_files
        file_keys = [file.file_key() for file in self._show_files(show_key)]
        return self._get_files_by_keys(file_keys)

    def _preload_season_files(
        self,
        season_keys: list[str],
        show_key: str,
        preloaded_files: Sequence[File] | None = None,
    ) -> Sequence[File]:
        if preloaded_files:
            return preloaded_files
        file_keys = [
            file.file_key()
            for season_key in season_keys
            for file in self._season_files(season_key, show_key)
        ]
        return self._get_files_by_keys(file_keys)

    def _preload_all_episode_files(
        self,
        season_keys: list[str],
        show_key: str,
        preloaded_files: Sequence[File] | None = None,
    ) -> Sequence[File]:
        if preloaded_files:
            return preloaded_files
        file_keys = [
            file.file_key()
            for season_key in season_keys
            for episode_key in self._episode_keys_from_file(season_key)
            for file in self._episode_files(episode_key, season_key, show_key)
        ]
        return self._get_files_by_keys(file_keys)

    def _preload_episode_files(
        self,
        episode_keys: list[str],
        season_key: str,
        show_key: str,
        preloaded_files: Sequence[File] | None = None,
    ) -> Sequence[File]:
        if preloaded_files:
            return preloaded_files
        file_keys = [
            file.file_key()
            for episode_key in episode_keys
            for file in self._episode_files(episode_key, season_key, show_key)
        ]
        return self._get_files_by_keys(file_keys)

    @abstractmethod
    def _season_keys_from_file(self, show_key: str) -> list[str]: ...

    @abstractmethod
    def _episode_keys_from_file(self, season_keys: str | list[str]) -> list[str]: ...
