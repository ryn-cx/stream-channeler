from collections.abc import Generator
from contextlib import ExitStack, contextmanager
from typing import Any
from unittest.mock import patch

from loguru import logger

from app.plugins.plugins.utils.base_plugin import BaseFile
from app.utils import tz_datetime


def _all_subclasses(cls: type) -> list[type]:
    """Recursively get all subclasses of a class."""
    result: list[type] = []
    for subclass in cls.__subclasses__():
        result.append(subclass)
        result.extend(_all_subclasses(subclass))
    return result


@contextmanager
def disable_ip_validation() -> Generator[None]:
    """Disable IP validation checks when downloading files."""
    with (
        patch("app.plugins.plugins.utils.ip_validator.check_ip_matches"),
        patch("app.plugins.plugins.utils.ip_validator.check_ip_not_matches"),
    ):
        yield


@contextmanager
def _patch_download(replacement: object) -> Generator[None]:
    """Patch _download on all BaseFile subclasses."""
    with ExitStack() as stack:
        for subclass in _all_subclasses(BaseFile):
            if "_download" in subclass.__dict__:
                stack.enter_context(patch.object(subclass, "_download", replacement))
        yield


@contextmanager
def mock_update() -> Generator[None]:
    """Mock _download to only update the timestamp instead of actually downloading."""

    def _mock(self: BaseFile[Any]) -> None:
        logger.debug(f"Mock Updating {self.database_entry.key}")
        self.database_entry.data_timestamp = tz_datetime.now()

    with _patch_download(_mock):
        yield


@contextmanager
def block_downloads() -> Generator[None]:
    """Raise an error if any file download is attempted."""

    def _block_downloads(self: BaseFile[Any]) -> None:
        msg = f"Unexpected download attempted: {self.database_entry.key}"
        raise RuntimeError(msg)

    with _patch_download(_block_downloads):
        yield


@contextmanager
def track_downloads() -> Generator[list[str]]:
    """Track which files are actually downloaded during an operation.

    Yields a list of files that were downloaded.
    """
    downloaded: list[str] = []

    def _track_downloads(self: BaseFile[Any]) -> None:
        downloaded.append(self.database_entry.key)

    with _patch_download(_track_downloads):
        yield downloaded
