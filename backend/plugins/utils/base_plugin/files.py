# TODO: Validate
import json
import time
from abc import ABC, abstractmethod
from collections.abc import Generator, Sequence
from contextlib import contextmanager
from datetime import datetime
from typing import Any, ClassVar, Protocol, final, overload, override
from xml.etree.ElementTree import Element, fromstring

from good_ass_pydantic_integrator.constants import INPUT_TYPE
from loguru import logger
from pydantic import BaseModel
from sqlmodel import Session

from app.plugins.models import File, Plugin
from app.utils import tz_datetime
from app.utils.sentinels import Sentinel

_UNLOADED = Sentinel("DATABASE_RECORD")


class BaseFile[T](ABC):
    IMMUTABLE: bool = False

    def __init__(self, session: Session, plugin: Plugin) -> None:
        """Initialize the file."""
        self.__session = session
        self.__plugin = plugin
        self._cached_parsed: T | None = None
        self.__database_record: File | None | Sentinel = _UNLOADED

    @property
    def _existing_database_record(self) -> File | None:
        if isinstance(self.__database_record, Sentinel):
            key = self.file_key()
            existing = File.get_from_memory(self.__session, self.__plugin, key)
            self.__database_record = existing or File.get(
                self.__session,
                self.__plugin,
                key,
            )
        return self.__database_record

    @_existing_database_record.setter
    def _existing_database_record(self, value: File | None) -> None:
        self.__database_record = value

    @property
    def database_record(self) -> File:
        """Return the underlying database File object."""
        if not self._existing_database_record:
            msg = "File has not been downloaded yet."
            raise ValueError(msg)
        return self._existing_database_record

    @property
    def data_timestamp(self) -> datetime:
        """Return the timestamp of the data in the file."""
        return self.database_record.data_timestamp

    unique_identifier: str

    def file_key(self) -> str:
        """Return the value for File.key."""
        return (
            f"{type(self).__name__}/{self.unique_identifier}{self._identifier_suffix()}"
        )

    @classmethod
    def file_key_to_unique_identifier(cls, file_key: str) -> str:
        """Convert File.key to the value that uniquely identifies this file."""
        return file_key.removeprefix(f"{cls.__name__}/").removesuffix(
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
        class_name = type(self).__name__
        action = "updated" if self._existing_database_record else "initial"
        # This log is useful when a download fails.
        logger.info(f"Downloading {action} {class_name} ({identifier})")
        start = time.monotonic()
        yield
        elapsed_time = time.monotonic() - start
        logger.info(
            f"Downloaded {action} {class_name} ({identifier}) in {elapsed_time:.2f}s",
        )

    @final  # Makes mocking downloads easier.
    def download_if_outdated(self, update_at: datetime | None = None) -> None:
        """Download the file if it is outdated."""
        if self.is_outdated(update_at):
            self._download()

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
    async def _async_download(self) -> None:
        """Asynchronously download the file."""
        msg = f"{type(self).__name__} does not implement async_download"
        raise NotImplementedError(msg)

    # This is not an abstractmethod because async_download or download must be
    # implemented, but not necessarily both.
    def _download(self) -> None:
        """Download the file."""
        msg = f"{type(self).__name__} does not implement _download"
        raise NotImplementedError(msg)

    def _write(self, content: str | None) -> None:
        """Write content to the file without committing to the database."""
        self._existing_database_record = File(
            key=self.file_key(),
            content=content,
            data_timestamp=tz_datetime.now(),
            plugin_id=self.__plugin.id,
        ).upsert(self.__plugin, self._existing_database_record)

        self._cached_parsed = None

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


class JSONFile[T](BaseFile[T], ABC):
    @abstractmethod
    # ANN401 - The input type is parsed JSON which is always Any.
    def _parse(self, raw: Any) -> T:  # noqa: ANN401
        """Parse raw JSON into a typed model."""

    def parsed(self) -> T:
        """Return the parsed content of the file."""
        if self._cached_parsed is None:
            if not (content := self.database_record.content):
                msg = "File content is empty, cannot parse."
                raise ValueError(msg)

            json_data = json.loads(content)
            self._cached_parsed = self._parse(json_data)
        return self._cached_parsed

    @override
    def _write(self, content: str | dict[str, Any] | list[Any] | None) -> None:
        if content is not None and not isinstance(content, str):
            content = json.dumps(content, default=str)
        super()._write(content)

    @classmethod
    @override
    def _identifier_suffix(cls) -> str:
        return ".json"


class XMLFile(BaseFile[Element], ABC):
    def __init__(
        self,
        session: Session,
        plugin: Plugin,
        unique_identifier: str,
    ) -> None:
        self.unique_identifier = unique_identifier
        super().__init__(session, plugin)

    def parsed(self) -> Element:
        """Return the parsed content of the file."""
        if self._cached_parsed is None:
            if not (content := self.database_record.content):
                msg = "File content is empty, cannot parse."
                raise ValueError(msg)
            self._cached_parsed = fromstring(content)  # noqa: S314
        return self._cached_parsed

    @classmethod
    @override
    def _identifier_suffix(cls) -> str:
        return ".xml"


class PartialGAPIJSON[T = BaseModel](JSONFile[T], ABC):
    api_endpoint: ClassVar[Any]

    acceptable_error: str | None = None

    def __init__(
        self,
        session: Session,
        plugin: Plugin,
        unique_identifier: str,
    ) -> None:
        self.unique_identifier = unique_identifier
        super().__init__(session, plugin)

    @override
    def _parse(self, raw: Any) -> T:
        return self.api_endpoint.parse(raw)  # type: ignore[return-value]

    @abstractmethod
    def _get(self) -> T:
        """Call the appropriate get method on the API endpoint."""

    def _get_acceptable_error(self) -> str | None:
        """Return the error message that should be caught during download.

        Override this for dynamic error messages that depend on instance state.
        """
        return self.acceptable_error

    def _download(self) -> None:
        with self._log_download(self.unique_identifier):
            try:
                response = self._get()
                content = self.api_endpoint.dump_response(response)
                self._write(content)
            except Exception as e:
                if str(e) != self._get_acceptable_error():
                    raise

                self._write(None)


class APISerializerEndpoint[T](Protocol):
    @classmethod
    def parse(cls, data: INPUT_TYPE, *, update_model: bool = True) -> T: ...

    @overload
    @staticmethod
    def dump_response(data: Sequence[BaseModel]) -> list[dict[str, Any]]: ...
    @overload
    @staticmethod
    def dump_response(data: BaseModel) -> dict[str, Any]: ...
    @staticmethod
    def dump_response(
        data: BaseModel | Sequence[BaseModel],
    ) -> dict[str, Any] | list[dict[str, Any]]: ...


class APIEndpoint[T](APISerializerEndpoint[T], Protocol):
    def get(self, unique_identifier: str, /) -> T: ...


class GAPIJSON[T: BaseModel](PartialGAPIJSON[T], ABC):
    api_endpoint: ClassVar[APIEndpoint[Any]]

    @override
    def _get(self) -> T:
        """Call the appropriate get method on the API endpoint."""
        return self.api_endpoint.get(self.unique_identifier)


# TODO: This may no longe be needed
class GAPIJSONNoGet[T: BaseModel](PartialGAPIJSON[T], ABC):
    api_endpoint: ClassVar[APISerializerEndpoint[Any]]


class GAPIListJSON[T: BaseModel](PartialGAPIJSON[list[T]], ABC):
    api_endpoint: ClassVar[APISerializerEndpoint[Any]]

    @override
    def _parse(self, raw: Any) -> list[T]:
        return [self.api_endpoint.parse(page) for page in raw]
