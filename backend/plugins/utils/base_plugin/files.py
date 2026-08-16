# TODO: Validate
import json
import time
from abc import ABC, abstractmethod
from collections.abc import Generator, Sequence
from contextlib import contextmanager
from datetime import datetime
from typing import Any, ClassVar, Final, Protocol, final, overload, override
from xml.etree.ElementTree import Element, fromstring

from bs4 import BeautifulSoup
from good_ass_pydantic_integrator import ParseLevel
from good_ass_pydantic_integrator.constants import INPUT_TYPE
from loguru import logger
from pydantic import BaseModel
from sqlmodel import Session, select

from app.files.models import File
from app.plugins.models import Plugin
from app.utils import tz_datetime
from app.utils.sentinels import Sentinel

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
    IMMUTABLE: bool = False

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
            msg = f"{self.file_key()} has not been downloaded."
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
    def is_outdated(self, minimum_timestamp: datetime | None = None) -> bool:
        """Check if the file is outdated."""
        if self.IMMUTABLE and self._existing_database_record:
            return False

        # If there is no database record the file is outdated.
        if not self._existing_database_record:
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
class JSONFile[T](BaseFile[T], ABC):
    # TODO: Validate
    @abstractmethod
    # ANN401 - The input type is parsed JSON which is always Any.
    def _parse(self, raw: Any) -> T:  # noqa: ANN401
        """Parse raw JSON into a typed model."""

    # TODO: Validate
    def parsed(self) -> T:
        """Return the parsed content of the file."""
        if self._cached_parsed is None:
            if not (content := self.database_record.content):
                msg = "File content is empty, cannot parse."
                raise ValueError(msg)

            json_data = json.loads(content)
            self._cached_parsed = self._parse(json_data)
        return self._cached_parsed

    # TODO: Validate
    @override
    def write(self, content: str | INPUT_TYPE | None, extra: str | None = None) -> None:
        if content is not None and not isinstance(content, str):
            content = json.dumps(content, default=str)
        super().write(content, extra)

    # TODO: Validate
    @classmethod
    @override
    def _identifier_suffix(cls) -> str:
        return ".json"


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
    def parsed(self) -> Element:
        """Return the parsed content of the file."""
        if self._cached_parsed is None:
            if not (content := self.database_record.content):
                msg = "File content is empty, cannot parse."
                raise ValueError(msg)
            self._cached_parsed = fromstring(content)  # noqa: S314
        return self._cached_parsed

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
    def parsed(self) -> BeautifulSoup:
        """Return the parsed content of the file."""
        if self._cached_parsed is None:
            if not (content := self.database_record.content):
                msg = "File content is empty, cannot parse."
                raise ValueError(msg)
            self._cached_parsed = BeautifulSoup(content, "html.parser")
        return self._cached_parsed

    # TODO: Validate
    @classmethod
    @override
    def _identifier_suffix(cls) -> str:
        return ".html"


# TODO: Validate
class PartialGAPIJSON[T = BaseModel](JSONFile[T], ABC):
    API_ENDPOINT: ClassVar[Any]

    ACCEPTABLE_ERROR: str | None = None

    PARSE_LEVEL: ClassVar[ParseLevel] = ParseLevel.UPDATE

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
    def _parse(self, raw: Any) -> T:
        return self.API_ENDPOINT.parse(raw, level=self.PARSE_LEVEL)  # type: ignore[no-any-return]

    # TODO: Validate
    @abstractmethod
    def _get(self) -> T:
        """Call the appropriate get method on the API endpoint."""

    # TODO: Validate
    def _get_ACCEPTABLE_ERROR(self) -> str | None:
        """Return the error message that should be caught during download.

        Override this for dynamic error messages that depend on instance state.
        """
        return self.ACCEPTABLE_ERROR

    # TODO: Validate
    def _is_acceptable_error(self, error: Exception) -> bool:
        """Return whether `error` should be caught during download.

        Override this to match on the exception type instead of its message.
        """
        return str(error) == self._get_ACCEPTABLE_ERROR()

    # TODO: Validate
    def acceptable_error_extra_value(self) -> str:
        return f"Invalid unique_identifier {self.unique_identifier}"

    # TODO: Validate
    def _download(self) -> None:
        with self._log_download(self.unique_identifier):
            try:
                response = self._get()
                content = self.API_ENDPOINT.original_input(response)
                self.write(content)
            except Exception as e:
                if not self._is_acceptable_error(e):
                    raise

                self.write(None, self.acceptable_error_extra_value())


# TODO: Validate
class APISerializerEndpoint[T](Protocol):
    # TODO: Validate
    @classmethod
    def parse(cls, data: INPUT_TYPE, *, level: ParseLevel = ParseLevel.UPDATE) -> T: ...

    # TODO: Validate
    @overload
    @staticmethod
    def original_input(data: Sequence[BaseModel]) -> list[INPUT_TYPE]: ...
    # TODO: Validate
    @overload
    @staticmethod
    def original_input(data: BaseModel) -> INPUT_TYPE: ...
    # TODO: Validate
    @staticmethod
    def original_input(
        data: BaseModel | Sequence[BaseModel],
    ) -> INPUT_TYPE | list[INPUT_TYPE]: ...

    # TODO: Validate
    @overload
    @staticmethod
    def model_dump(data: Sequence[BaseModel]) -> list[INPUT_TYPE]: ...
    # TODO: Validate
    @overload
    @staticmethod
    def model_dump(data: BaseModel) -> INPUT_TYPE: ...
    # TODO: Validate
    @staticmethod
    def model_dump(
        data: BaseModel | Sequence[BaseModel],
    ) -> INPUT_TYPE | list[INPUT_TYPE]: ...


# TODO: Validate
class APIEndpoint[T](APISerializerEndpoint[T], Protocol):
    # TODO: Validate
    def download_and_parse(self, unique_identifier: str, /) -> T: ...


# TODO: Validate
class GAPIJSON[T: BaseModel](PartialGAPIJSON[T], ABC):
    API_ENDPOINT: ClassVar[APIEndpoint[Any]]

    # TODO: Validate
    @override
    def _get(self) -> T:
        """Call the appropriate get method on the API endpoint."""
        return self.API_ENDPOINT.download_and_parse(self.unique_identifier)


# TODO: This may no longe be needed
# TODO: Validate
class GAPIJSONNoGet[T: BaseModel](PartialGAPIJSON[T], ABC):
    API_ENDPOINT: ClassVar[APISerializerEndpoint[Any]]


# TODO: Validate
class GAPIListJSON[T: BaseModel](PartialGAPIJSON[list[T]], ABC):
    API_ENDPOINT: ClassVar[APISerializerEndpoint[Any]]

    # TODO: Validate
    @override
    def _parse(self, raw: Any) -> list[T]:
        return [self.API_ENDPOINT.parse(page, level=self.PARSE_LEVEL) for page in raw]
