# TODO: Validate
from collections.abc import Generator
from contextlib import ExitStack, contextmanager
from datetime import timedelta
from pathlib import Path
from typing import Any
from unittest.mock import patch

from loguru import logger

from app.plugins.plugins.utils.base_plugin import BaseFile


def _all_subclasses(cls: type) -> list[type]:
    """Recursively get all subclasses of a class."""
    result: list[type] = []
    for subclass in cls.__subclasses__():
        result.append(subclass)
        result.extend(_all_subclasses(subclass))
    return result


@contextmanager
def _patch_download(replacement: object) -> Generator[None]:
    """Patch _download on all BaseFile subclasses."""
    with ExitStack() as stack:
        for subclass in _all_subclasses(BaseFile):
            if "_download" in subclass.__dict__:
                stack.enter_context(patch.object(subclass, "_download", replacement))
        yield


@contextmanager
def mock_update(files_directory: Path) -> Generator[None]:
    """Mock _download to increment data_timestamp instead of actually downloading."""

    def _mock(self: BaseFile[Any]) -> None:
        key = self.database_record.key
        logger.debug(f"Mock Updating {key}")
        self.database_record.data_timestamp += timedelta(minutes=1)

    with _patch_download(_mock):
        yield


@contextmanager
def block_downloads() -> Generator[None]:
    """Raise an error if any file download is attempted."""

    def _block_downloads(self: BaseFile[Any]) -> None:
        msg = f"Unexpected download attempted: {self.database_record.key}"
        raise RuntimeError(msg)

    with _patch_download(_block_downloads):
        yield


@contextmanager
def track_downloads() -> Generator[list[str]]:
    """Track which files are actually downloaded during an operation.

    Yields a list of files that were downloaded.
    """
    originals: dict[type, Any] = {}
    for subclass in _all_subclasses(BaseFile):
        if "_download" in subclass.__dict__:
            originals[subclass] = subclass.__dict__["_download"]

    downloaded: list[str] = []

    def _track_downloads(self: BaseFile[Any]) -> None:
        for cls in type(self).__mro__:
            if cls in originals:
                originals[cls](self)
                break
        downloaded.append(self.database_record.key)

    with _patch_download(_track_downloads):
        yield downloaded
