# TODO: Validate
from __future__ import annotations

from abc import ABC
from collections.abc import Mapping, Sequence
from datetime import datetime
from itertools import chain
from typing import Any

from app.titles.models import Title
from plugins.utils.base_plugin.file_access import BaseFileAccessMixin
from plugins.utils.base_plugin.files import BaseFile


# TODO: Validate
class BaseUpsertFilesMixin(BaseFileAccessMixin, ABC):
    def _title_files(self, title_key: str) -> Sequence[BaseFile[Any]]:
        """Return the files required to upsert the title.

        The default implementation will raise because returning an empty list is more
        error-prone than explicitly raising an error."""
        raise NotImplementedError

    def _season_files(
        self,
        season_key: str,
        title_key: str,
    ) -> Sequence[BaseFile[Any]]:
        """Return the files required to upsert the season.

        The default implementation will raise because returning an empty list is more
        error-prone than explicitly raising an error."""
        raise NotImplementedError

    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        title_key: str,
    ) -> Sequence[BaseFile[Any]]:
        """Return the files required to upsert the episode.

        The default implementation will raise because returning an empty list is more
        error-prone than explicitly raising an error."""
        raise NotImplementedError

    def _season_keys_from_title_files(self, title_key: str) -> list[str]:
        """Return the season keys from the title's files."""
        raise NotImplementedError

    def _episode_keys_from_season_files(
        self,
        season_keys: str | list[str],
        title_key: str,
    ) -> list[str]:
        """Return the episode keys from the season's files."""
        raise NotImplementedError

    def _preload_and_download_title_files(
        self,
        title_key: str,
        update_at: datetime | None,
    ) -> None:
        """Preload and download all title files for a title."""
        title_files = self._title_files(title_key)
        self._preload_files(title_files)
        self._download_if_outdated(title_files, update_at)

    def _preload_and_download_season_files(
        self,
        title_key: str,
        update_ats: Mapping[str, datetime | None],
    ) -> None:
        """Preload and download all season files for a title."""
        files_by_season_key = {
            season_key: self._season_files(season_key, title_key)
            for season_key in self._season_keys_from_title_files(title_key)
        }
        self._preload_files(list(chain.from_iterable(files_by_season_key.values())))
        for season_key, season_files in files_by_season_key.items():
            self._download_if_outdated(season_files, update_ats.get(season_key))

    def _preload_and_download_episode_files(
        self,
        title_key: str,
        update_ats: Mapping[tuple[str, str], datetime | None],
    ) -> None:
        """Preload and download all episode files for a title."""
        files_by_episode_key = {
            (season_key, episode_key): self._episode_files(
                episode_key,
                season_key,
                title_key,
            )
            for season_key in self._season_keys_from_title_files(title_key)
            for episode_key in self._episode_keys_from_season_files(
                season_key,
                title_key,
            )
        }
        self._preload_files(list(chain.from_iterable(files_by_episode_key.values())))
        for episode_key, episode_files in files_by_episode_key.items():
            self._download_if_outdated(episode_files, update_ats.get(episode_key))

    def _preload_and_download_files(self, title: Title | str) -> None:
        """Preload and download all title, season, and episode files for a title."""
        title_key: str
        title_update_at: datetime | None
        season_update_ats: dict[str, datetime | None]
        episode_update_ats: dict[tuple[str, str], datetime | None]
        if isinstance(title, str):
            title_key = title
            title_update_at = None
            season_update_ats = {}
            episode_update_ats = {}
        else:
            title_key = title.key
            title_update_at = title.update_at
            season_update_ats = {
                season.key: season.update_at for season in title.seasons
            }
            episode_update_ats = {
                (season.key, episode.key): episode.update_at
                for season in title.seasons
                for episode in season.episodes
            }

        self._preload_and_download_title_files(title_key, title_update_at)
        self._preload_and_download_season_files(title_key, season_update_ats)
        self._preload_and_download_episode_files(title_key, episode_update_ats)

    # TODO: Validate
    def _title_files_data_timestamp(self, title_key: str) -> datetime:
        return min(file.record_data_timestamp for file in self._title_files(title_key))

    # TODO: Validate
    def _season_files_data_timestamp(self, season_key: str, title_key: str) -> datetime:
        files = self._season_files(season_key, title_key)
        return min(file.record_data_timestamp for file in files)

    # TODO: Validate
    def _episode_files_data_timestamp(
        self,
        episode_key: str,
        season_key: str,
        title_key: str,
    ) -> datetime:
        files = self._episode_files(episode_key, season_key, title_key)
        return min(file.record_data_timestamp for file in files)
