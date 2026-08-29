# TODO: Validate
import json
import time
from abc import ABC, abstractmethod
from collections.abc import Generator
from contextlib import contextmanager
from datetime import datetime
from typing import (
    Any,
    Final,
    Protocol,
    cast,
    final,
    override,
)
from xml.etree.ElementTree import Element, fromstring

from bs4 import BeautifulSoup
from loguru import logger
from sqlmodel import Session, select

from app.files.models import File
from app.plugins.models import Plugin
from app.utils import tz_datetime
from app.utils.sentinels import Sentinel
from plugins.utils.get_around_client import get_around_client

# What `File.extra` says about a file that has been read to the end. `extra` is an
# object now, so the mark is a field of it rather than the whole of it, which
# leaves room for a second thing to be said about a file later.
EXTRA_STATUS_FIELD = "status"
COMPLETED_STATUS = "Completed"


_UNLOADED = Sentinel("DATABASE_RECORD")

INITIAL_FILE_IDENTIFIER: Final = "Initial"
"""What a file keyed by a timestamp is identified by before there is one.

The first of a series of timestamped files has no earlier file to catch up to,
so it is named for being the first rather than for when it was downloaded. That
keeps its key the same every time one is created from nothing, which a key made
of the current time never is.
"""


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
    def database_record(self) -> File:
        """Return the underlying database File object.

        The file must already be downloaded; callers are responsible for calling
        `download_if_outdated()` first. Reading a record never triggers a download.
        """
        record = self._existing_database_record
        if record is None:
            msg = (
                f"{self.__class__.__name__}/{self.file_key()} has not been downloaded."
            )
            raise ValueError(msg)
        return record

    # TODO: Validate
    @property
    def data_timestamp(self) -> datetime:
        """Return the timestamp of the data in the file."""
        return self.database_record.data_timestamp

    # TODO: Cam tjos be simplified so it doesn't need to return the record?
    # TODO: Validate
    @staticmethod
    def raise_if_not_is_instance[InstanceT](
        value: object,
        expected_type: type[InstanceT],
    ) -> InstanceT:
        """Return `value` narrowed to `expected_type`, raising if it is not one."""
        if not isinstance(value, expected_type):
            msg = f"Expected {expected_type.__name__}, got {type(value).__name__}."
            raise TypeError(msg)
        return value

    unique_identifier: str

    # TODO: Validate
    def identifier_datetime(self) -> datetime:
        """Return the datetime the identifier names, or now for the initial file."""
        if self.unique_identifier == INITIAL_FILE_IDENTIFIER:
            return tz_datetime.now()
        return tz_datetime.fromisoformat(self.unique_identifier)

    # TODO: Validate
    @override
    def __eq__(self, other: object) -> bool:
        return isinstance(other, BaseFile) and self.file_key() == other.file_key()

    # TODO: Validate
    @override
    def __hash__(self) -> int:
        return hash(self.file_key())

    # TODO: Validate
    def file_key(self) -> str:
        """Return the value for File.key."""
        return (
            f"{type(self).__name__}/{self.unique_identifier}{self._identifier_suffix()}"
        )

    # TODO: Validate
    def log_id(self) -> str:
        return f"{self.__plugin.key} - {self.file_key()}"

    # TODO: Validate
    @classmethod
    def file_key_to_unique_identifier(cls, file_key: str) -> str:
        """Convert File.key to the value that uniquely identifies this file."""
        return file_key.removeprefix(f"{cls.__name__}/").removesuffix(
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
        class_name = type(self).__name__
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
    @final  # Makes mocking downloads easier.
    async def async_download_if_outdated(
        self,
        update_at: datetime | None = None,
    ) -> None:
        """Asynchronously download the file if it is outdated."""
        if self.is_outdated(update_at):
            await self._async_download()

    # This is not an abstractmethod because async_download or download must be
    # implemented, but not necessarily both.
    # TODO: Validate
    async def _async_download(self) -> None:
        """Asynchronously download the file."""
        msg = f"{type(self).__name__} does not implement async_download"
        raise NotImplementedError(msg)

    # This is not an abstractmethod because async_download or download must be
    # implemented, but not necessarily both.
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
    def write(self, content: str | None, extra: str | None = None) -> None:
        """Write content to the file and commit it to the database.

        The record is committed through a session of its own so a download is kept
        even when the import that triggered it fails. Committing the plugin's
        session here would also commit the records that import has upserted so far,
        which is what used to leave a failed import half stored.
        """
        with Session(self.__session.get_bind()) as file_session:
            plugin = file_session.exec(
                select(Plugin).where(Plugin.id == self.__plugin.id),
            ).one()
            File(
                key=self.file_key(),
                content=content,
                data_timestamp=tz_datetime.now(),
                extra=extra,
                plugin_id=plugin.id,
                update_at=self._next_update_at(),
            ).upsert_and_set_update_at(
                plugin,
                File.get(file_session, plugin, self.file_key()),
            )
            file_session.commit()

        # The record the file session wrote belongs to that session, so the plugin's
        # own copy is reloaded to pick the new values up.
        self._existing_database_record = File.get(
            self.__session,
            self.__plugin,
            self.file_key(),
            populate_existing=True,
        )
        self._cached_parsed = None

    # TODO: Validate
    @abstractmethod
    def _parse(self, content: str) -> T:
        """Read the stored file into the value `parsed` answers with."""

    # TODO: Validate
    def _stored_content(self) -> str:
        if not (content := self.database_record.content):
            msg = "File content is empty, cannot parse."
            raise ValueError(msg)
        return content

    # TODO: Validate
    @final
    def parsed(self) -> T:
        """Return the parsed content of the file."""
        if self._cached_parsed is None:
            self._cached_parsed = self._parse(self._stored_content())
        return self._cached_parsed

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
        return self.data_timestamp < minimum_timestamp


# TODO: Validate
class TextFile(BaseFile[str], ABC):
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
class XMLFile(BaseFile[Element], ABC):
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
    def _parse(self, content: str) -> Element:
        return fromstring(content)  # noqa: S314

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
    def acceptable_error_extra_value(self) -> str:
        return f"Invalid unique_identifier {self.unique_identifier}"

    # TODO: Validate
    @override
    def _download(self) -> None:
        with self._log_download(self.unique_identifier):
            try:
                data = self._download_file()
            except Exception as error:
                if not self._is_acceptable_error(error):
                    raise
                self.write(None, self.acceptable_error_extra_value())
            else:
                self.write(data)

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
