import json
import time
from abc import ABC, abstractmethod
from collections.abc import Generator
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime
from typing import (
    Any,
    Protocol,
    final,
    override,
)

from loguru import logger
from sqlmodel import Session

from app.files.models import File
from app.plugins.models import Plugin
from app.utils import tz_datetime
from app.utils.sentinels import Sentinel

_UNLOADED = Sentinel("DATABASE_RECORD")

_file_updates_bypassed: ContextVar[bool] = ContextVar(
    "file_updates_bypassed",
    default=False,
)


# TODO: Validate
@contextmanager
def bypass_file_updates() -> Generator[None]:
    """Download only the files that are missing for the duration of the block.

    A reimport reads what has already been downloaded again, so a file that is
    merely due for its next update is left as it is and only a file with no
    record at all is fetched.
    """
    token = _file_updates_bypassed.set(True)
    try:
        yield
    finally:
        _file_updates_bypassed.reset(token)


class BaseFile[T](ABC):
    custom_class_key: str | None = None

    def __init__(
        self,
        session: Session,
        plugin: Plugin,
        unique_identifier: str,
    ) -> None:
        """Initialize the file."""
        self.unique_identifier = unique_identifier
        self.__session = session
        self.__plugin = plugin
        self._cached_parsed: T | None = None
        self.__database_record: File | None | Sentinel = _UNLOADED
        """The database record, None (no record exists), or a Sentinel (the database
        record may or may not exist).

        This property is required because the files classes are initialized to get the
        file names then all of the files are preloaded from the database so there is no
        way to initialize the class with the database record already loaded."""

    @property
    def _database_record(self) -> File | None:
        # When downloading a file to validate the URL download_if_outdated will be
        # called on a File with no database record so this lookup is required for that
        # niche situation.
        if isinstance(self.__database_record, Sentinel):
            self.__database_record = File.get(
                self.__session,
                self.__plugin,
                self.file_key(),
            )
        return self.__database_record

    @_database_record.setter
    def _database_record(self, value: File | None) -> None:
        self.__database_record = value

    def preload_record(self, record: File | None) -> None:
        """Preload the database record for the file.

        The main purpose of this function is to save a reference to the database record
        for the file, so it does not get garbage collected prematurely."""
        self._database_record = record

    # It's impossible to make any of the _existing_database_record functions truely type
    # safe so a lot of type ignores are required.
    @property
    def record_content(self) -> str | None:
        """Return the content of the file's database record."""
        return self._database_record.content  # type: ignore[union-attr]

    @property
    def record_key(self) -> str:
        """Return the key of the file's database record."""
        return self._database_record.key  # type: ignore[union-attr]

    @property
    def record_extra(self) -> dict[str, Any]:
        """Return the extra metadata of the file's database record."""
        return self._database_record.extra  # type: ignore[union-attr]

    @property
    def record_status(self) -> str | None:
        """Return the status of the file's database record."""
        return self._database_record.status  # type: ignore[union-attr]

    @property
    def record_update_at(self) -> datetime | None:
        """Return the update timestamp of the file's database record."""
        return self._database_record.update_at  # type: ignore[union-attr]

    @property
    def record_data_timestamp(self) -> datetime:
        """Return the data_timestamp from the file record."""
        return self._database_record.data_timestamp  # type: ignore[union-attr]

    def clear_status(self) -> None:
        """Set a file's database record status to None."""
        self._database_record.status = None  # type: ignore[union-attr]

    def clear_update_at(self) -> None:
        """Set a file's database record update timestamp to None."""
        self._database_record.update_at = None  # type: ignore[union-attr]

    @override
    def __eq__(self, other: object) -> bool:
        return isinstance(other, BaseFile) and self.file_key() == other.file_key()

    @override
    def __hash__(self) -> int:
        return hash(self.file_key())

    @classmethod
    def class_key(cls) -> str:
        """Return the class key used as a prefix in the file key."""
        return cls.custom_class_key or cls.__name__

    def file_key(self) -> str:
        """Return the value used to identify the file and saved in File.key."""
        return (
            f"{type(self).class_key()}/{self.unique_identifier}"
            f"{self._identifier_suffix()}"
        )

    def log_id(self) -> str:
        return f"{self.__plugin.key} - {self.file_key()}"

    @classmethod
    def file_to_unique_identifier(cls, file: File) -> str:
        """Return the unique identifier for a file.

        The unique identifier is the `File.key` without the class prefix and without the
        file type extension."""
        return file.key.removeprefix(f"{cls.class_key()}/").removesuffix(
            cls._identifier_suffix(),
        )

    @classmethod
    @abstractmethod
    def _identifier_suffix(cls) -> str:
        """Return the file identifier suffix.

        This is a file extension like .json, .xml, .html, etc.
        """

    @contextmanager
    def _log_download(self, identifier: str) -> Generator[None]:
        """Context manager that logs downloads."""
        class_name = type(self).class_key()
        plugin_key = self.__plugin.key
        action = "updated" if self._database_record else "initial"
        # This log is useful when a download fails.
        logger.info(f"Downloading {action} {plugin_key} {class_name} ({identifier})")
        start = time.monotonic()
        yield
        elapsed_time = time.monotonic() - start
        logger.info(
            f"Downloaded {action} {plugin_key} {class_name} ({identifier}) "
            f"in {elapsed_time:.2f}s",
        )

    # TODO: Validate
    @final  # _download_file should be overridden instead.
    def download_if_outdated(self, update_at: datetime | None = None) -> None:
        """Download the file if it is outdated."""
        if _file_updates_bypassed.get() and self._database_record:
            return
        if self.is_outdated(update_at):
            self._download_and_write()

    @abstractmethod
    def _download_file(self) -> str | None:
        """Download the file and return the body as it was served."""

    def _is_acceptable_error(self, error: Exception) -> bool:  # noqa: ARG002
        """Return whether `error` should be allowed during a download.

        If an error is allowed an empty file will be witten to the database to indicate
        the failure."""
        return False

    def _initial_status_after_downloading(self) -> str | None:
        """Return the initial value for `File.status` after completing a download."""
        return None

    def _download_and_write(self) -> None:
        """Download and write the file to the database with pretty logging."""
        with self._log_download(self.unique_identifier):
            try:
                data = self._download_file()
            except Exception as error:
                if not self._is_acceptable_error(error):
                    raise
                self.write(None, "Invalid")
            else:
                self.write(data, self._initial_status_after_downloading())

    def _next_update_at(self) -> datetime | None:
        """Set the frequency that the file should be updated."""
        return None

    def write(self, content: str | None, status: str | None = None) -> None:
        """Write the content and status to the database."""
        record = File(
            key=self.file_key(),
            content=content,
            data_timestamp=tz_datetime.now(),
            status=status,
            plugin_id=self.__plugin.id,
        ).upsert(self.__plugin, self._database_record)
        record.set_update_at(self._next_update_at())
        self._database_record = record
        self._cached_parsed = None
        self.__session.flush()

    @abstractmethod
    def _parse(self, content: str) -> T:
        """Parse the file's content and returns the parsed representation.

        This is the internal function called by _parsed set by child implementations
        that determine how the file's content is parsed."""

    @final
    def content(self) -> str:
        """Return the content of the file."""
        if not (content := self.record_content):
            msg = f"{self.class_key()}/{self.file_key()} has no content."
            raise ValueError(msg)
        return content

    @final
    def parsed(self) -> T:
        """Return the parsed content of the file, caching the response."""
        if self._cached_parsed is None:
            self._cached_parsed = self._parse(self.content())
        return self._cached_parsed

    def does_not_exist(self) -> bool:
        """Return whether the file has been downloaded."""
        return self._database_record is None

    def is_outdated(self, minimum_timestamp: datetime | None = None) -> bool:
        """Return whether the file is outdated."""
        # If there is no database record the file is outdated.
        if not self._database_record:
            return True

        record_update_at = self.record_update_at
        # If there is an update_at value that is in the past but newer than the file's
        # data_timestamp it is outdated.
        if (
            record_update_at
            and record_update_at <= tz_datetime.now()
            and self._database_record.data_timestamp < record_update_at
        ):
            return True

        # If there is no minimum timestamp and the file exists it is up to date.
        if not minimum_timestamp:
            return False

        # If the timestamp is in the future it is impossible to make the file up to date
        # so the file cannot be outdated.
        if minimum_timestamp > tz_datetime.now():
            return False

        # If the file is older than the minimum timestamp it is outdated.
        return self._database_record.data_timestamp < minimum_timestamp


class TextFile(BaseFile[str], ABC):
    @override
    def _parse(self, content: str) -> str:
        return content

    @classmethod
    @override
    def _identifier_suffix(cls) -> str:
        return ".txt"


class Endpoint[T](Protocol):
    def load(self, data: str, log_id: str = "") -> T: ...


class SingleArgEndpoint[T](Endpoint[T], Protocol):
    def download(self, unique_identifier: str, /) -> str: ...


class IntegerArgEndpoint[T](Endpoint[T], Protocol):
    def download(self, unique_identifier: int, /) -> str: ...


class NoArgsEndpoint[T](Endpoint[T], Protocol):
    def download(self) -> str: ...


class PagedEndpoint[T](Endpoint[T], Protocol):
    def download_all(self, unique_identifier: str, /) -> list[str]: ...


class APIClientFile[T](BaseFile[T], ABC):
    @abstractmethod
    def _endpoint(self) -> Endpoint[Any]:
        """Return the endpoint used to download the file.

        The file suffix defaults to json because most API client files deal with JSON
        fils."""

    @classmethod
    @override
    def _identifier_suffix(cls) -> str:
        return ".json"


class MultipleArgEndpointFile[T](APIClientFile[T], ABC):
    """Base class to use when endpoint.download() takes multiple args.

    There is no default implementation for `_download_file` because there is no
    reasonable way to predict what parameters it will take.

    Other endpoints subclass this out of convenience because the biggest difference
    betweeen it and the single arguement classes is that those ones have more functions
    that can be implemented in the base file class."""

    @abstractmethod
    @override
    def _endpoint(self) -> Endpoint[T]: ...

    @override
    def _parse(self, content: str) -> T:
        return self._endpoint().load(content, self.log_id())


class SingleArgEndpointFile[T](MultipleArgEndpointFile[T], ABC):
    """Base class to use when `endpoint.download()` takes a single `str | int` arg."""

    @abstractmethod
    @override
    def _endpoint(self) -> SingleArgEndpoint[T]: ...

    @override
    def _download_file(self) -> str:
        return self._endpoint().download(self.unique_identifier)


class NoArgsEndpointFile[T](MultipleArgEndpointFile[T], ABC):
    """Base class to use when `endpoint.download()` takes no args."""

    @abstractmethod
    @override
    def _endpoint(self) -> NoArgsEndpoint[T]: ...

    def __init__(self, session: Session, plugin: Plugin) -> None:
        super().__init__(session, plugin, self.unique_identifier)

    @override
    def _download_file(self) -> str:
        return self._endpoint().download()


class IntegerArgEndpointFile[T](MultipleArgEndpointFile[T], ABC):
    """Base class to use when `endpoint.download()` takes a single `int` arg."""

    @abstractmethod
    @override
    def _endpoint(self) -> IntegerArgEndpoint[T]: ...

    @override
    def _download_file(self) -> str:
        return self._endpoint().download(int(self.unique_identifier))


class PagedEndpointFile[T](APIClientFile[list[T]], ABC):
    """Base class to use when `endpoint.download_all()` takes a single `str | int` arg."""

    @abstractmethod
    @override
    def _endpoint(self) -> PagedEndpoint[T]: ...

    @override
    def _download_file(self) -> str:
        downloaded_files = self._endpoint().download_all(self.unique_identifier)
        return json.dumps(downloaded_files)

    @override
    def _parse(self, content: str) -> list[T]:
        files: list[str] = json.loads(content)
        return [self._endpoint().load(file, self.log_id()) for file in files]
