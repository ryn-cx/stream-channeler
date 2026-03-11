# TODO: Validate
import json
from abc import ABC, abstractmethod
from collections.abc import Generator
from contextlib import contextmanager
from datetime import datetime
from typing import Any, final, override

from loguru import logger
from sqlmodel import Session

from app.plugins.models import File, Plugin
from app.plugins.schemas import FileInput
from app.utils import tz_datetime


class BaseFile[T](ABC):
    IMMUTABLE: bool = False

    # region Initialization

    def __init__(self, db: Session, plugin: Plugin) -> None:
        """Initialize the file.

        Will automatically load the File object from the database if it is available in
        the current session.
        """
        self.__db = db
        self.__plugin = plugin
        self._cached_parsed: T | None = None
        self._database_entry: File | None = None

        file_key = self.file_key(self.unique_identifier())
        existing_database_entry = File.get_from_memory(db, plugin, file_key)
        self._database_entry = existing_database_entry or File.get(db, plugin, file_key)

    # endregion Initialization

    # region Getters
    @property
    def database_entry(self) -> File:
        """Return the underlying database File object."""
        if not self._database_entry:
            msg = "File has not been downloaded yet."
            raise ValueError(msg)
        return self._database_entry

    def get_data_timestamp(self) -> datetime:
        """Return File.data_timestamp."""
        return self.database_entry.data_timestamp

    # endregion Getters

    # region Key/Identifier

    @classmethod
    def file_key(cls, unique_identifier: str) -> str:
        """Return the value for File.key."""
        return f"{cls.__name__}/{unique_identifier}{cls._identifier_suffix()}"

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

    @abstractmethod
    def unique_identifier(self) -> str:
        """Return the value that uniquely identifies this file."""

    # endregion Key/Identifier

    # region Download

    @contextmanager
    def _log_download(self, identifier: str) -> Generator[None]:
        """Context manager that logs downloads."""
        class_name = self.__class__.__name__
        action = "Updating" if self._database_entry else "Downloading"
        logger.info(f"{action} {class_name} for {identifier}")
        yield
        logger.info(f"Finished {action.lower()} {class_name} for {identifier}")

    @final  # Makes mocking downloads easier.
    def download_if_outdated(self, update_at: datetime | None = None) -> None:
        """Download the file if it is outdated."""
        if self._is_outdated(update_at):
            self._download()

    @final  # Makes mocking downloads easier.
    async def async_download_if_outdated(
        self,
        update_at: datetime | None = None,
    ) -> None:
        """Asynchronously download the file if it is outdated."""
        if self._is_outdated(update_at):
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

    # endregion Download

    def _write(self, content: str | None) -> None:
        """Write content to the file and immediately commit it to the database."""
        self._database_entry = FileInput(
            key=self.file_key(self.unique_identifier()),
            content=content,
            data_timestamp=tz_datetime.now(),
        ).upsert(self.__plugin, self._database_entry)

        self.__db.commit()
        self._cached_parsed = None

    def _is_outdated(self, minimum_timestamp: datetime | None = None) -> bool:
        """Check if the file is outdated."""
        if self.IMMUTABLE and self._database_entry:
            return False

        # If there is no database entry the file is outdated.
        if not self._database_entry:
            return True

        # If there is no minimum timestamp and the file exists it is up to date.
        if not minimum_timestamp:
            return False

        # If the timestamp is in the future it is impossible to make the file up to date
        # so the file cannot be outdated.
        if minimum_timestamp > tz_datetime.now():
            return False

        # If the file is older than the minimum timestamp it is outdated.
        return self.get_data_timestamp() < minimum_timestamp

    def get_content(self) -> str | None:
        """Return the file content if it has been downloaded, otherwise None."""
        if not self._database_entry:
            return None
        return self._database_entry.content


class JSONFile[T](BaseFile[T], ABC):
    @abstractmethod
    # ANN401 - The input type is parsed JSON which is always Any.
    def _parse(self, raw: Any) -> T:  # noqa: ANN401
        """Parse raw JSON into a typed model."""

    def parsed(self) -> T:
        """Return the parsed content of the file."""
        if self._cached_parsed is None:
            if not (content := self.get_content()):
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
