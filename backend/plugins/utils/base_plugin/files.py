# TODO: Validate
import json
import time
from abc import ABC, abstractmethod
from collections.abc import Generator
from contextlib import contextmanager
from datetime import datetime
from typing import (
    Any,
    Protocol,
    cast,
    final,
    override,
)
from xml.etree import ElementTree  # noqa: ICN001

from bs4 import BeautifulSoup
from loguru import logger
from sqlmodel import Session

from app.files.models import File
from app.plugins.models import Plugin
from app.utils import tz_datetime
from app.utils.sentinels import Sentinel
from plugins.utils.get_around_client import get_around_client

INCOMPLETE_STATUS = "Incomplete"


_UNLOADED = Sentinel("DATABASE_RECORD")


# TODO: Validate
class BaseFile[T](ABC):
    # TODO: Validate
    def __init__(self, session: Session, plugin: Plugin) -> None:
        """Initialize the file."""
        self.__session = session
        self.__plugin = plugin
        self._cached_parsed: T | None = None
        self.__database_record: File | None | Sentinel = _UNLOADED

    # TODO: Validate
    @property
    def _existing_database_record(self) -> File | None:
        if isinstance(self.__database_record, Sentinel):
            key = self.file_key()
            # The fallback File.get should only occur during tests when importing files
            existing = File.get_from_memory(self.__session, self.__plugin, key)
            self.__database_record = existing or File.get(
                self.__session,
                self.__plugin,
                key,
            )
        return self.__database_record

    # TODO: Validate
    @_existing_database_record.setter
    def _existing_database_record(self, value: File | None) -> None:
        self.__database_record = value

    # TODO: Validate
    @property
    def _database_record(self) -> File:
        """Return the underlying database File object.

        The file must already be downloaded; callers are responsible for calling
        `download_if_outdated()` first. Reading a record never triggers a download.
        """
        record = self._existing_database_record
        if record is None:
            msg = f"{self.class_key()}/{self.file_key()} has not been downloaded."
            raise ValueError(msg)
        return record

    @property
    def record_content(self) -> str | None:
        """Return the content of the file's database record."""
        return self._database_record.content

    @property
    def record_key(self) -> str:
        """Return the key of the file's database record."""
        return self._database_record.key

    @property
    def record_extra(self) -> dict[str, Any]:
        """Return the extra metadata of the file's database record."""
        return self._database_record.extra

    @property
    def record_status(self) -> str | None:
        """Return the status of the file's database record."""
        return self._database_record.status

    @property
    def record_update_at(self) -> datetime | None:
        """Return the update timestamp of the file's database record."""
        return self._database_record.update_at

    def clear_status(self) -> None:
        """Set a file's database record status to None."""
        self._database_record.status = None

    def clear_update_at(self) -> None:
        """Set a file's database record update timestamp to None."""
        self._database_record.update_at = None

    # TODO: Validate
    def data_timestamp(self) -> datetime:
        """Return the timestamp of the data in the file."""
        self.download_if_outdated()
        return self._database_record.data_timestamp

    unique_identifier: str

    # TODO: Validate
    @override
    def __eq__(self, other: object) -> bool:
        return isinstance(other, BaseFile) and self.file_key() == other.file_key()

    # TODO: Validate
    @override
    def __hash__(self) -> int:
        return hash(self.file_key())

    custom_class_key: str | None = None

    # TODO: Validate
    @classmethod
    def class_key(cls) -> str:
        return cls.custom_class_key or cls.__name__.removeprefix("_")

    # TODO: Validate
    def file_key(self) -> str:
        """Return the value for File.key."""
        return (
            f"{type(self).class_key()}/{self.unique_identifier}"
            f"{self._identifier_suffix()}"
        )

    # TODO: Validate
    def log_id(self) -> str:
        return f"{self.__plugin.key} - {self.file_key()}"

    # TODO: Validate
    @classmethod
    def file_to_unique_identifier(cls, file: File) -> str:
        """Return the unique identifier for a file.

        The unique identifier is the `File.key` without the class prefix and without the
        file type extension."""
        return file.key.removeprefix(f"{cls.class_key()}/").removesuffix(
            cls._identifier_suffix(),
        )

    # TODO: Validate
    @classmethod
    @abstractmethod
    def _identifier_suffix(cls) -> str:
        """Return the file identifier suffix.

        This is a file extension like .json, .xml, .html, etc.
        """

    # TODO: Validate
    @contextmanager
    def _log_download(self, identifier: str) -> Generator[None]:
        """Context manager that logs downloads."""
        class_name = type(self).class_key()
        plugin_key = self.__plugin.key
        action = "new" if self._existing_database_record else "initial"
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
    @final  # Makes mocking downloads easier.
    def download_if_outdated(self, update_at: datetime | None = None) -> None:
        """Download the file if it is outdated."""
        if self.is_outdated(update_at):
            self._download()

    # TODO: Validate
    def _download(self) -> None:
        """Download the file."""
        msg = f"{type(self).__name__} does not implement _download"
        raise NotImplementedError(msg)

    # TODO: Validate
    def _next_update_at(self) -> datetime | None:
        """Return when the file should be downloaded again, if it should be."""
        return None

    # TODO: Validate
    def write(self, content: str | None, status: str | None = None) -> None:
        record = File(
            key=self.file_key(),
            content=content,
            data_timestamp=tz_datetime.now(),
            status=status,
            plugin_id=self.__plugin.id,
        ).upsert(self.__plugin, self._existing_database_record)
        record.set_update_at(self._next_update_at())
        self._existing_database_record = record
        self._cached_parsed = None
        self.__session.flush()

    # TODO: Validate
    @abstractmethod
    def _parse(self, content: str) -> T:
        """Read the stored file into the value `parsed` answers with."""

    # TODO: Validate
    @final
    def content(self) -> str:
        self.download_if_outdated()
        if not (content := self.record_content):
            msg = f"{self.class_key()}/{self.file_key()} has no content."
            raise ValueError(msg)
        return content

    # TODO: Validate
    @final
    def parsed(self) -> T:
        if self._cached_parsed is None:
            self._cached_parsed = self._parse(self.content())
        return self._cached_parsed

    # TODO: Deprecate, this is sloppy as shit.
    @final
    def parsed_or_none(self) -> T | None:
        """Return what the file holds, or None where it was stored empty.

        What TMDB has no answer for is stored as a row with no content, which is
        what says the question was asked and came back with nothing. That is not
        a failure to read, so it is answered with nothing rather than raised.
        """
        self.download_if_outdated()
        if not self.record_content:
            return None
        return self.parsed()

    # TODO: Validate
    def does_not_exist(self) -> bool:
        """Report whether the file has never been stored."""
        return self._existing_database_record is None

    # TODO: Validate
    def is_outdated(self, minimum_timestamp: datetime | None = None) -> bool:
        """Check if the file is outdated."""
        # If there is no database record the file is outdated.
        if not self._existing_database_record:
            return True

        # A file that asked to be downloaded again by now is outdated whatever it
        # is being read against, so a file type that refreshes on its own says so
        # once through `_next_update_at` rather than every caller passing a
        # timestamp it has no reason to know.
        record_update_at = self._existing_database_record.update_at
        if record_update_at and record_update_at <= tz_datetime.now():
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


# TODO: Validate
class TextFile(BaseFile[str], ABC):
    # TODO: Validate
    def __init__(
        self,
        session: Session,
        plugin: Plugin,
        unique_identifier: str,
    ) -> None:
        self.unique_identifier = unique_identifier
        super().__init__(session, plugin)

    # TODO: Validate
    @override
    def _parse(self, content: str) -> str:
        return content

    # TODO: Validate
    @classmethod
    @override
    def _identifier_suffix(cls) -> str:
        return ".txt"


# TODO: Validate
class XMLFile(BaseFile[ElementTree.Element], ABC):
    # TODO: Validate
    def __init__(
        self,
        session: Session,
        plugin: Plugin,
        unique_identifier: str,
    ) -> None:
        self.unique_identifier = unique_identifier
        super().__init__(session, plugin)

    # TODO: Validate
    @override
    def _parse(self, content: str) -> ElementTree.Element:
        return ElementTree.fromstring(content)  # noqa: S314

    # TODO: Validate
    @classmethod
    @override
    def _identifier_suffix(cls) -> str:
        return ".xml"


# TODO: Validate
class HTMLFile(BaseFile[BeautifulSoup], ABC):
    # TODO: Validate
    def __init__(
        self,
        session: Session,
        plugin: Plugin,
        unique_identifier: str,
    ) -> None:
        self.unique_identifier = unique_identifier
        super().__init__(session, plugin)

    # TODO: Validate
    @abstractmethod
    def _url(self) -> str:
        """Return the address the page is served from."""

    # TODO: Validate
    @override
    def _download(self) -> None:
        with self._log_download(self.unique_identifier):
            response = get_around_client().get(self._url(), follow_redirects=True)
            response.raise_for_status()
            self.write(response.text)

    # TODO: Validate
    @override
    def _parse(self, content: str) -> BeautifulSoup:
        return BeautifulSoup(content, "html.parser")

    # TODO: Validate
    @classmethod
    @override
    def _identifier_suffix(cls) -> str:
        return ".html"


# TODO: Validate
class Endpoint[T](Protocol):
    # TODO: Validate
    def load(self, data: str, log_id: str = "") -> T: ...


# TODO: Validate
class LoadEndpoint[T](Endpoint[T], Protocol):
    # TODO: Validate
    def download(self, unique_identifier: str, /) -> str: ...


# TODO: Validate
class IntegerLoadEndpoint[T](Endpoint[T], Protocol):
    # TODO: Validate
    def download(self, unique_identifier: int, /) -> str: ...


# TODO: Validate
class PagedLoadEndpoint[T](Endpoint[T], Protocol):
    # TODO: Validate
    def download_all(self, unique_identifier: str, /) -> list[str]: ...


# TODO: Validate
class DownloadedFile[T](BaseFile[T], ABC):
    # TODO: Validate
    @abstractmethod
    def _endpoint(self) -> Endpoint[Any]: ...

    # TODO: Validate
    def __init__(
        self,
        session: Session,
        plugin: Plugin,
        unique_identifier: str,
    ) -> None:
        self.unique_identifier = unique_identifier
        super().__init__(session, plugin)

    # TODO: Validate
    def _download_file(self) -> str:
        """Download the file and return the body as it was served."""
        endpoint = cast("LoadEndpoint[T]", self._endpoint())
        return endpoint.download(self.unique_identifier)

    # TODO: Validate
    def _is_acceptable_error(self, error: Exception) -> bool:  # noqa: ARG002
        """Return whether `error` should be caught during download."""
        return False

    # TODO: Validate
    def acceptable_error_status(self) -> str:
        return f"Invalid unique_identifier {self.unique_identifier}"

    # TODO: Validate
    def _initial_status_after_downloading(self) -> str | None:
        return None

    # TODO: Validate
    @override
    def _download(self) -> None:
        with self._log_download(self.unique_identifier):
            try:
                data = self._download_file()
            except Exception as error:
                if not self._is_acceptable_error(error):
                    raise
                self.write(None, self.acceptable_error_status())
            else:
                self.write(data, self._initial_status_after_downloading())

    # TODO: Validate
    @classmethod
    @override
    def _identifier_suffix(cls) -> str:
        return ".json"


# TODO: Validate
class EndpointFile[T](DownloadedFile[T], ABC):
    # TODO: Validate
    @abstractmethod
    @override
    def _endpoint(self) -> Endpoint[T]: ...

    # TODO: Validate
    @override
    def _parse(self, content: str) -> T:
        return self._endpoint().load(content, self.log_id())


# TODO: Validate
class IntegerEndpointFile[T](EndpointFile[T], ABC):
    # TODO: Validate
    @abstractmethod
    @override
    def _endpoint(self) -> IntegerLoadEndpoint[T]: ...

    # TODO: Validate
    @override
    def _download_file(self) -> str:
        return self._endpoint().download(int(self.unique_identifier))


# TODO: Validate
class PagedEndpointFile[T](DownloadedFile[list[T]], ABC):
    # TODO: Validate
    @abstractmethod
    @override
    def _endpoint(self) -> Endpoint[T]: ...

    # TODO: Validate
    def _download_pages(self) -> list[str]:
        """Download every page of the file, first to last."""
        endpoint = cast("PagedLoadEndpoint[T]", self._endpoint())
        return endpoint.download_all(self.unique_identifier)

    # TODO: Validate
    @override
    def _download_file(self) -> str:
        return json.dumps(self._download_pages())

    # TODO: Validate
    @override
    def _parse(self, content: str) -> list[T]:
        pages: list[str] = json.loads(content)
        endpoint = self._endpoint()
        return [endpoint.load(page, self.log_id()) for page in pages]
