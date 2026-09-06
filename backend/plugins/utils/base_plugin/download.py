# TODO: Validate
"""Which files a stored record is read out of, and how old what they hold is."""

from abc import ABC
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlmodel import Session, col, select

from app.files.models import File
from app.plugins.models import Plugin
from plugins.utils.base_plugin.files import BaseFile


# TODO: Validate
class BaseDownloadMixin(ABC):
    file_session: Session
    file_plugin: Plugin

    # TODO: Validate
    def _show_files(self, show_key: str) -> Sequence[BaseFile[Any]]:
        """Return the files associated with the show."""
        msg = "This plugin does not have show specific files."
        raise NotImplementedError(msg)

    # TODO: Validate
    def _season_files(
        self,
        season_key: str,
        show_key: str,
    ) -> Sequence[BaseFile[Any]]:
        """Return the files associated with the season."""
        msg = "This plugin does not have season specific files."
        raise NotImplementedError(msg)

    # TODO: Validate
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        show_key: str,
    ) -> Sequence[BaseFile[Any]]:
        """Return the files associated with the episode."""
        msg = "This plugin does not have episode specific files."
        raise NotImplementedError(msg)

    # TODO: Validate
    def _plugin_files(self) -> Sequence[BaseFile[Any]]:
        """Return the files associated with the plugin."""
        msg = "This plugin does not have plugin specific files."
        raise NotImplementedError(msg)

    # TODO: Validate
    def _source_files(self) -> Sequence[BaseFile[Any]]:
        """Return the files associated with the source."""
        msg = "This plugin does not have source specific files."
        raise NotImplementedError(msg)

    # TODO: Validate
    @staticmethod
    def _download_if_outdated(
        files: Sequence[BaseFile[Any]],
        update_at: datetime | None = None,
    ) -> None:
        """Download each of `files` that is missing or older than `update_at`.

        For where something has been told which files moved and when, rather than
        for reading them: a change TMDB reports names a file and a moment, and
        neither is known at the point the file is next read.
        """
        for file in files:
            file.download_if_outdated(update_at)

    # TODO: Validate
    def show_data_timestamp(self, show_key: str) -> datetime:
        """Return the data timestamp for the show's files."""
        return self._show_files(show_key)[0].data_timestamp()

    # TODO: Validate
    def season_data_timestamp(self, season_key: str, show_key: str) -> datetime:
        """Return the data timestamp for the season's files."""
        return self._season_files(season_key, show_key)[0].data_timestamp()

    # TODO: Validate
    def episode_data_timestamp(
        self,
        episode_key: str,
        season_key: str,
        show_key: str,
    ) -> datetime:
        """Return the data timestamp for the episode's files."""
        return self._episode_files(
            episode_key,
            season_key,
            show_key,
        )[0].data_timestamp()

    # TODO: Validate
    def source_data_timestamp(self) -> datetime:
        return self._source_files()[0].data_timestamp()

    # TODO: Validate
    @staticmethod
    def _file_timestamps(files: Sequence[BaseFile[Any]]) -> list[datetime]:
        return [file.data_timestamp() for file in files]

    # TODO: Validate
    def show_data_timestamps(self, show_key: str) -> list[datetime]:
        """Return the data timestamp of each of the show's files."""
        return self._file_timestamps(self._show_files(show_key))

    # TODO: Validate
    def season_data_timestamps(self, season_key: str, show_key: str) -> list[datetime]:
        """Return the data timestamp of each of the season's files."""
        return self._file_timestamps(self._season_files(season_key, show_key))

    # TODO: Validate
    def episode_data_timestamps(
        self,
        episode_key: str,
        season_key: str,
        show_key: str,
    ) -> list[datetime]:
        """Return the data timestamp of each of the episode's files."""
        return self._file_timestamps(
            self._episode_files(episode_key, season_key, show_key),
        )

    # TODO: Validate
    def _get_files_by_keys(self, file_keys: list[str]) -> Sequence[File]:
        if not file_keys:
            return []
        statement = select(File).where(
            File.plugin_id == self.file_plugin.id,
            col(File.key).in_(file_keys),
        )
        return self.file_session.exec(statement).all()

    # TODO: Validate
    def _download_show_files_and_children(
        self,
        show_key: str,
        update_at: datetime | None = None,
    ) -> None:
        self._download_if_outdated(self._show_files(show_key), update_at)
        for season_key in self._season_keys_from_show_files(show_key):
            self._download_if_outdated(self._season_files(season_key, show_key))
            for episode_key in self._episode_keys_from_season_files(
                season_key,
                show_key,
            ):
                self._download_if_outdated(
                    self._episode_files(episode_key, season_key, show_key),
                )

    # TODO: Validate
    def _season_keys_from_show_files(self, show_key: str) -> list[str]:
        msg = "This plugin does not have season keys from file."
        raise NotImplementedError(msg)

    # TODO: Validate
    def _episode_keys_from_season_files(
        self,
        season_keys: str | list[str],
        show_key: str,
    ) -> list[str]:
        msg = "This plugin does not have episode keys from file."
        raise NotImplementedError(msg)
