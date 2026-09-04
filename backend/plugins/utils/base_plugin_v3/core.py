# TODO: Validate
"""What every part of a plugin is built on: who it is, and what it holds open."""

from __future__ import annotations

import weakref
from abc import ABC, abstractmethod
from collections.abc import Callable, Sequence
from datetime import date
from typing import TYPE_CHECKING, Any, ClassVar

from sqlalchemy import event
from sqlmodel import Session, col, select

from app.files.models import File
from app.plugins.models import Plugin
from app.sources.models import Source
from app.utils import tz_datetime
from plugins.utils.base_plugin_v3.files import INITIAL_FILE_IDENTIFIER, BaseFile

if TYPE_CHECKING:
    from plugins.utils.base_plugin_v3.importer import BaseImporter
    from plugins.utils.base_plugin_v3.initialize import BasePluginInitializer

FILE_SESSION_KEY = "plugin_file_session"


# TODO: Validate
def file_session_for(session: Session) -> Session:
    """Return the session the plugin's files are read and written through.

    Files are downloaded while media is being written rather than beforehand, so
    the two cannot share a session. A media write that is rolled back would take
    the downloads made along the way out with it, and a file committed where it
    stands would carry half-written media out with it. One file session is opened
    per media session and shared by every plugin reading through that session.

    It commits ahead of the media session, so whatever was written from a file
    has that file stored behind it, and it closes with the media session it was
    opened for.
    """
    existing: Session | None = session.info.get(FILE_SESSION_KEY)
    if existing is not None:
        return existing

    # Bound to whatever the media session is bound to. Against an engine that is
    # a connection and a transaction of its own, which is what a running app
    # wants. Against a connection - which is what a test holding everything in
    # one uncommitted transaction hands out - it joins that transaction as a
    # savepoint, so the file session reads what the test put there.
    file_session = Session(
        session.get_bind(),
        join_transaction_mode="create_savepoint",
    )
    session.info[FILE_SESSION_KEY] = file_session

    event.listen(session, "before_commit", lambda _session: file_session.commit())
    weakref.finalize(session, file_session.close)
    return file_session


# TODO: Validate
class BasePluginCore(ABC):
    """The session, the stored plugin, and the names the plugin goes by."""

    session: Session
    file_session: Session
    plugin: Plugin
    file_plugin: Plugin
    _sources: dict[str, Source]
    _file_cache: dict[object, Any]
    initializer: ClassVar[type[BasePluginInitializer]]
    importer: ClassVar[type[BaseImporter]]

    # TODO: Validate
    def __init__(
        self,
        session: Session,
        plugin: Plugin | None = None,
        sources: Sequence[Source] | None = None,
    ) -> None:
        self.session = session
        self.file_session = file_session_for(session)
        self._file_cache = {}
        self.plugin = (
            plugin if plugin is not None else Plugin.get_one(session, self.plugin_name())
        )
        self.file_plugin = Plugin.get_one(self.file_session, self.plugin_name())
        source_list = sources if sources is not None else self.plugin.sources
        self._sources = {source.key: source for source in source_list}

    # TODO: Validate
    @classmethod
    @abstractmethod
    def plugin_name(cls) -> str: ...

    # TODO: Validate
    @classmethod
    @abstractmethod
    def favicon_url(cls) -> str | None: ...

    # TODO: Validate
    @classmethod
    def name_on_tmdb(cls) -> tuple[str, ...]:
        return (cls.plugin_name(),)

    # TODO: Validate
    @classmethod
    def _source_keys(cls) -> tuple[str, ...]:
        return (cls.plugin_name(),)

    # TODO: Validate
    @classmethod
    def matches_tmdb_provider(cls, provider_name: str) -> bool:
        return provider_name in cls.name_on_tmdb()

    # TODO: Validate
    def clear_file_cache(self) -> None:
        self._file_cache.clear()

    # TODO: Validate
    def _file[FileT: BaseFile[Any]](
        self,
        file_type: Callable[..., FileT],
        *identifiers: object,
    ) -> FileT:
        """Return the cached `file_type` instance for `identifiers`."""
        cache_key = (file_type, identifiers)
        cached: FileT | None = self._file_cache.get(cache_key)
        if cached is not None:
            return cached
        file = file_type(self.file_session, self.file_plugin, *identifiers)
        self._file_cache[cache_key] = file
        return file

    # TODO: Validate
    @staticmethod
    def _get_date_from_file_name(file_class: type[BaseFile[Any]], stored: File) -> date:
        identifier = file_class.file_to_unique_identifier(stored)
        return date.fromisoformat(identifier.split("/")[-1])

    # TODO: Validate
    def latest_file_record(
        self,
        file_class: type[BaseFile[Any]],
        file_prefix: str,
    ) -> File | None:
        statement = (
            select(File)
            .where(
                File.plugin == self.plugin,
                col(File.key).startswith(f"{file_class.class_key()}/{file_prefix}"),
            )
            .order_by(col(File.data_timestamp).desc())
        )
        return self.session.exec(statement).first()

    # TODO: Validate
    def files_with_prefix(
        self,
        file_class: type[BaseFile[Any]],
        key_prefix: str,
    ) -> Sequence[File]:
        statement = select(File).where(
            File.plugin == self.plugin,
            col(File.key).startswith(f"{file_class.class_key()}/{key_prefix}"),
        )
        return self.session.exec(statement).all()

    # TODO: Validate
    def latest_file_date(
        self,
        file_class: type[BaseFile[Any]],
        file_prefix: str,
    ) -> date:
        stored = self.latest_file_record(file_class, file_prefix)
        if stored is None:
            return tz_datetime.now().date()
        return self._get_date_from_file_name(file_class, stored)

    # TODO: Validate
    def _initial_file[FileT: BaseFile[Any]](
        self,
        file_type: Callable[..., FileT],
    ) -> FileT:
        """Return the `file_type` instance a timestamped series of files starts at."""
        return self._file(file_type, INITIAL_FILE_IDENTIFIER)
