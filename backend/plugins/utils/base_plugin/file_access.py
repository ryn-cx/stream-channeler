from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy.orm import defer
from sqlmodel import Session, col, select

from app.files.models import File
from app.plugins.models import Plugin
from plugins.utils.abstract_plugin import InvalidURLError
from plugins.utils.base_plugin.files import BaseFile


# TODO: Validate
class BaseFileAccessMixin(ABC):
    session: Session
    plugin: Plugin
    _file_cache: dict[tuple[type[BaseFile[Any]], Any], BaseFile[Any]]

    # TODO: Validate
    @classmethod
    @abstractmethod
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
    def _download_if_outdated(
        files: Sequence[BaseFile[Any]],
        update_at: datetime | None = None,
    ) -> None:
        """Download all of `files` that are missing or outdated."""
        for file in files:
            file.download_if_outdated(update_at)

    # TODO: Validate
    def _preload_files(
        self,
        files: Sequence[BaseFile[Any]],
        *,
        load_content: bool = True,
    ) -> None:
        """Preload the given files into the session cache."""
        file_keys = [file.file_key() for file in files]
        statement = select(File).where(
            File.plugin_id == self.plugin.id,
            col(File.key).in_(file_keys),
        )
        if not load_content:
            statement = statement.options(defer(File.content))  # type: ignore[arg-type]
        records = self.session.exec(statement).all()
        records_by_key = {record.key: record for record in records}
        for file in files:
            file.preload_record(records_by_key.get(file.file_key()))

    def raise_invalid_url_if_no_content(self, file: BaseFile[Any], url: str) -> None:
        """Raise an InvalidURLError if the given file has no content."""
        try:
            file.download_if_outdated()
            file.content()
        except ValueError as error:
            msg = f"Invalid {self.plugin_name()} URL: {url}"
            raise InvalidURLError(msg) from error
