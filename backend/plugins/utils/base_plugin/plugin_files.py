# TODO: Validate
from __future__ import annotations

from abc import ABC
from collections.abc import Callable, Iterable, Mapping, Sequence
from datetime import datetime
from typing import Any

from sqlalchemy.engine.result import ScalarResult
from sqlalchemy.orm import selectinload
from sqlmodel import col, select

from app.files.models import File
from app.seasons.models import Season
from app.sources.models import Source
from app.titles.models import Title
from plugins.utils.base_plugin.files import BaseFile
from plugins.utils.base_plugin.source import BaseSourceMixin
from plugins.utils.constants import INCOMPLETE_STATUS


# TODO: Validate
class BasePluginFilesMixin(BaseSourceMixin, ABC):
    def _plugin_files(self) -> Sequence[BaseFile[Any]]:
        """Return the files required to upsert the plugin."""
        raise NotImplementedError

    def _plugin_files_data_timestamps(self) -> list[datetime]:
        """Return the data timestamp from each of the plugin's files."""
        return [file.record_data_timestamp for file in self._plugin_files()]

    # TODO: Validate
    def _title_keys_from_plugin_files(self) -> Iterable[str]:
        raise NotImplementedError

    # TODO: Validate
    def _plugin_files_or_empty(self) -> Sequence[BaseFile[Any]]:
        try:
            return self._plugin_files()
        except NotImplementedError:
            return []

    # TODO: Validate
    def _source_files_or_empty(self) -> Sequence[BaseFile[Any]]:
        try:
            return self._source_files()
        except NotImplementedError:
            return []

    # TODO: Validate
    @staticmethod
    def _holds_record(files: Sequence[BaseFile[Any]], record: File) -> bool:
        return any(file.file_key() == record.key for file in files)

    # TODO: Validate
    def is_source_file(self, record: File) -> bool:
        return self._holds_record(self._source_files_or_empty(), record)

    # TODO: Validate
    def is_plugin_file(self, record: File) -> bool:
        return self._holds_record(self._plugin_files_or_empty(), record)

    # TODO: Validate
    def handles_file(self, record: File) -> bool:
        return self.is_source_file(record) or self.is_plugin_file(record)

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

    def _preload_sources(
        self,
        source_key: str | list[str] | None = None,
        *,
        preload_titles: bool = False,
        preload_seasons: bool = False,
        preload_episodes: bool = False,
    ) -> ScalarResult[Source]:
        """Preload the sources with optional related titles, seasons, and episodes.

        If no source_key is provided, all sources for the plugin will be preloaded.
        """
        options: list[Any] = []
        if preload_episodes:
            options.append(
                selectinload(Source.titles)  # type: ignore[arg-type]
                .selectinload(Title.seasons)  # type: ignore[arg-type]
                .selectinload(Season.episodes),  # type: ignore[arg-type]
            )
        elif preload_seasons:
            options.append(
                selectinload(Source.titles).selectinload(Title.seasons),  # type: ignore[arg-type]  # type: ignore[arg-type]
            )
        elif preload_titles:
            options.append(selectinload(Source.titles))  # type: ignore[arg-type]

        statement = select(Source).where(Source.plugin_id == self.plugin.id)

        if isinstance(source_key, list):
            statement = statement.where(Source.key.in_(source_key))  # type: ignore[attr-defined]
        elif source_key:
            statement = statement.where(Source.key == source_key)
        return self.session.exec(statement.options(*options)).unique()

    # TODO: Validate
    def _mark_titles_with_changed_listings(
        self,
        source_key: str | None,
        listings: Mapping[str, object],
        data_timestamp: datetime,
    ) -> None:
        for source in self._preload_sources(source_key, preload_seasons=True):
            for title in source.titles:
                if title.key not in listings:
                    continue
                listing = listings[title.key]
                previous = title.extra.get("listing", listing)
                if previous != listing:
                    title.set_update_at(data_timestamp)
                    for season in title.seasons:
                        season.set_update_at(data_timestamp)
                if title.extra.get("listing") != listing:
                    title.extra = {**title.extra, "listing": listing}

    # TODO: Validate
    def _mark_mismatched_titles_as_outdated(
        self,
        source_key: str | None,
        new_title_keys: Iterable[str],
        data_timestamp: datetime,
    ) -> None:
        """Mark `Title`s as outdated if they are mismatched with the `new_title_keys`.

        Mismatched means one of the following:
            Title is listed in new_title_keys but is marked as deleted
            Title is not in new_title_keys but is not marked as deleted.
        """
        new_title_keys = set(new_title_keys)
        for source in self._preload_sources(source_key, preload_titles=True):
            for title in source.titles:
                is_listed = title.key in new_title_keys
                is_deleted = title.deleted_at is not None
                if is_listed == is_deleted:
                    title.set_update_at(data_timestamp)
