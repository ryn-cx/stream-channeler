# TODO: Validate
import json
from abc import ABC, abstractmethod
from collections.abc import Generator
from contextlib import contextmanager
from datetime import datetime
from functools import cache
from typing import Any, override

from loguru import logger
from sqlmodel import Session

from app.media.models import File, Plugin
from app.media.schemas import FileInput
from app.utils import tz_datetime


class BaseFile[T](ABC):
    IMMUTABLE: bool = False

    # region Initialization

    def __init__(self, db: Session, plugin: Plugin) -> None:
        """Initialize the file.

        Checks the database for the file, and if the file does not exist, downloads it.
        """
        self.__db = db
        self.__plugin = plugin
        file_key = self.__file_key()

        if file_from_memory := File.get_from_memory(db, plugin, file_key):
            self._database_entry_ = file_from_memory
        # This is a safeguard that makes developing easier that should never actually
        # occur in production due to its poor performance.
        elif file_from_db := File.get(db, plugin, file_key):
            self._database_entry_ = file_from_db
        else:
            self._download()

        self._cached_parsed: T | None = None

    # endregion

    # region Getters/Setters

    def set_file_extra(self, extra_value: str) -> None:
        """Set the value of File.extra."""
        self._database_entry_.extra = extra_value

    def _get_file_content(self) -> str:
        """Return the value of File.content."""
        return self._database_entry_.content

    def get_file_data_timestamp(self) -> datetime:
        """Return the value of File.data_timestamp."""
        return self._database_entry_.data_timestamp

    # endregion

    # region Key/Identifier

    def __file_key(self) -> str:
        """Return the value for File.key."""
        return self.__class__.file_key(self.unique_identifier())

    @classmethod
    @cache
    def file_key(cls, unique_identifier: str) -> str:
        """Return the value for File.key.

        Alternative to __file_key that can be used without an instance of the class
        because initializing the class could cause a database query and a download.
        """
        return f"{cls.__name__}/{unique_identifier}{cls._identifier_suffix()}"

    @classmethod
    @cache
    def file_key_to_unique_identifier(cls, file_key: str) -> str:
        """Convert File.key to the unique identifier."""
        return file_key.removeprefix(f"{cls.__name__}/").removesuffix(
            cls._identifier_suffix(),
        )

    @classmethod
    @abstractmethod
    @cache
    def _identifier_suffix(cls) -> str:
        """Return the file identifier suffix.

        This is a file extension like .json, .xml, or .html.
        """

    @abstractmethod
    def unique_identifier(self) -> str:
        """Return the value that uniquely identifies the file."""

    # endregion

    # region Download

    @contextmanager
    def _log_download(self, identifier: str) -> Generator[None]:
        """Context manager that logs download start, completion, and failure."""
        class_name = self.__class__.__name__
        if getattr(self, "_database_entry_", None):
            action = "Updating"
        else:
            action = "Downloading"
        logger.info(f"{action} {class_name} for {identifier}")
        yield
        logger.info(f"Finished {action.lower()} {class_name} for {identifier}")

    def download_if_outdated(self, update_at: datetime | None = None) -> None:
        """Download the file if it is outdated."""
        if self.IMMUTABLE and getattr(self, "_database_entry_", None):
            msg = "This file is immutable and cannot be updated once downloaded."
            raise ValueError(msg)

        if self._is_outdated(update_at):
            self._download()

    async def async_download_if_outdated(
        self,
        minimum_timestamp: datetime | None = None,
    ) -> None:
        """Asynchronously download the file if it is outdated."""
        if self._is_outdated(minimum_timestamp):
            await self._async_download()

    # This is not an abstractmethod because async_download or download must be
    # implemented, but not necessarily both.
    async def _async_download(self) -> None:
        """Asynchronously download the file."""
        msg = f"{self.__class__.__name__} does not implement async_download"
        raise NotImplementedError(msg)

    # This is not an abstractmethod because async_download or download must be
    # implemented, but not necessarily both.
    def _download(self) -> None:
        """Download the file."""
        msg = f"{self.__class__.__name__} does not implement _download"
        raise NotImplementedError(msg)

    # endregion

    def _write(self, content: str) -> None:
        """Write content to the file and immediately commit to the database."""
        self._database_entry_ = FileInput(
            key=self.__file_key(),
            content=content,
            data_timestamp=tz_datetime.now(),
        ).upsert(self.__plugin, getattr(self, "_database_entry_", None))

        self.__db.commit()
        self._cached_parsed = None

    def _is_outdated(self, minimum_timestamp: datetime | None = None) -> bool:
        """Check if the file is outdated."""
        # If there is no database entry the file is outdated.
        if not getattr(self, "_database_entry_", None):
            return True

        # If there is no minimum timestamp and the file exists it is up to date.
        if not minimum_timestamp:
            return False

        # If the timestamp is in the future it is impossible for the file to be up to
        # date so it is not outdated.
        if minimum_timestamp > tz_datetime.now():
            return False

        # If the file is older than the minimum timestamp it is outdated.
        return self._database_entry_.data_timestamp < minimum_timestamp

    def has_file_content(self) -> str:
        """Return whether the file has content.

        Actually returns a string, but it can be treated as a boolean.
        """
        return self._get_file_content()


class JSONFile[T](BaseFile[T], ABC):
    @abstractmethod
    # ANN401 - The input type is parsed JSON which is always Any.
    def _parse(self, raw: Any) -> T:  # noqa: ANN401
        """Transform raw JSON into a typed model."""

    def parsed(self) -> T:
        """Return the parsed content of the file."""
        if not self._cached_parsed:
            content = self._get_file_content()
            json_data = json.loads(content)
            self._cached_parsed = self._parse(json_data)
        return self._cached_parsed

    @override
    def _write(self, content: str | dict[str, Any] | list[Any]) -> None:
        if not isinstance(content, str):
            content = json.dumps(content, default=str)
        super()._write(content)

    @classmethod
    @cache
    @override
    def _identifier_suffix(cls) -> str:
        return ".json"
