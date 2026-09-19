from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable, Iterable, Mapping, Sequence
from datetime import date, datetime
from itertools import chain
from typing import Any, override

from sqlmodel import Session, col, select

from app.files.models import File
from app.plugins.models import Plugin
from app.titles.models import Title
from plugins.utils.abstract_plugin import AbstractPlugin, InvalidURLError
from plugins.utils.base_plugin.files import (
    BaseFile,
)
from plugins.utils.constants import INCOMPLETE_STATUS


# TODO: Validate
class BaseFileAccessMixin(AbstractPlugin, ABC):
    session: Session
    plugin: Plugin
    _file_cache: dict[tuple[type[BaseFile[Any]], Any], BaseFile[Any]]

    @classmethod
    @abstractmethod
    @override
    def plugin_name(cls) -> str: ...

    def _cached_file[FileT: BaseFile[Any]](
        self,
        file_type: type[FileT],
        *identifiers: object,
    ) -> FileT:
        """Return the cached file for the given `file_type` and `identifiers`."""
        cache_key = (file_type, identifiers)
        if cached := self._file_cache.get(cache_key):
            # _file_cache includes cached files from every file type in a single
            # dict which loses type safety but as long as _file_cache is only accessed
            # through _cached_file this should be type safe.
            return cached  # type: ignore[return-value]
        file = file_type(self.session, self.plugin, *identifiers)
        self._file_cache[cache_key] = file
        return file

    @staticmethod
    def _date_from_file_name(file_class: type[BaseFile[Any]], stored: File) -> date:
        """Extract the date from the file name of the given stored file."""
        identifier = file_class.file_to_unique_identifier(stored)
        return date.fromisoformat(identifier.split("/")[-1])

    def latest_file_record(
        self,
        file_class: type[BaseFile[Any]],
        file_prefix: str | int | None = None,
    ) -> File | None:
        """Return the latest file record for the given `file_class` and `file_prefix`.

        If no matching file is found, `None` is returned.

        The file's data_timestamp is used to determine which file is the latest.

        Args:
            file_class: The class of the file to look for.
            file_prefix: The prefix of the file key to match. Every file of
            `file_class` is matched when it is None.
        """
        key_prefix: str
        if file_prefix is None:
            key_prefix = f"{file_class.class_key()}/"
        else:
            key_prefix = f"{file_class.class_key()}/{file_prefix}/"

        return self.session.exec(
            select(File)
            .where(
                File.plugin_id == self.plugin.id,
                col(File.key).startswith(key_prefix),
            )
            .order_by(col(File.data_timestamp).desc()),
        ).first()

    @staticmethod
    def _download_if_outdated(
        files: Sequence[BaseFile[Any]],
        update_at: datetime | None = None,
    ) -> None:
        """Download all of `files` that are missing or outdated."""
        for file in files:
            file.download_if_outdated(update_at)

    def _preload_files(self, files: Sequence[BaseFile[Any]]) -> None:
        """Preload the given files into the session cache."""
        file_keys = [file.file_key() for file in files]
        records = self.session.exec(
            select(File).where(
                File.plugin_id == self.plugin.id,
                col(File.key).in_(file_keys),
            ),
        ).all()
        records_by_key = {record.key: record for record in records}
        for file in files:
            file.preload_record(records_by_key.get(file.file_key()))

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

    def _download_initial_files(self, title_key: str) -> None:
        """Download all of the initial title, season, and episode files for a `Title`."""
        self._preload_and_download_files(title_key)

    def _download_outdated_files(self, title: Title) -> None:
        """Download all of the outdated title, season, and episode files for a `Title`."""
        self._preload_and_download_files(title)

    def _incomplete_files[T: BaseFile[Any]](
        self,
        file_class: type[T],
        factory: Callable[[File], T],
        *,
        key_prefix: str | int = "",
    ) -> list[T]:
        """Return all of the incomplete files for the given file class and key prefix."""
        prefix = f"{key_prefix}/" if key_prefix != "" else ""
        statement = (
            select(File)
            .where(
                File.plugin_id == self.plugin.id,
                col(File.key).startswith(f"{file_class.class_key()}/{prefix}"),
                File.status == INCOMPLETE_STATUS,
            )
            .order_by(col(File.data_timestamp).asc())
        )
        return [factory(file) for file in self.session.exec(statement).all()]

    def raise_invalid_url_if_no_content(self, file: BaseFile[Any], url: str) -> None:
        """Raise an InvalidURLError if the given file has no content."""
        try:
            file.download_if_outdated()
            file.content()
        except ValueError as error:
            msg = f"Invalid {self.plugin_name()} URL: {url}"
            raise InvalidURLError(msg) from error

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

    def _plugin_files(self) -> Sequence[BaseFile[Any]]:
        """Return the files required to upsert the plugin."""
        raise NotImplementedError

    # TODO: Validate
    def _title_keys_from_plugin_files(self) -> Iterable[str]:
        raise NotImplementedError

    def _source_files(self) -> Sequence[BaseFile[Any]]:
        """Return the files required to upsert the source.

        The default implementation will raise because returning an empty list is more
        error-prone than explicitly raising an error."""
        raise NotImplementedError

    def _plugin_files_data_timestamps(self) -> list[datetime]:
        """Return the data timestamp from each of the plugin's files."""
        return [file.record_data_timestamp for file in self._plugin_files()]

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

    # TODO: Validate
    def _source_files_data_timestamp(self) -> datetime:
        return min(file.record_data_timestamp for file in self._source_files())

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
