# TODO: Validate
"""Context managers for PluginValidator."""

from collections.abc import Generator
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Any
from unittest.mock import patch

from loguru import logger

from plugins.utils.base_plugin import BaseFile


@contextmanager
def mock_update() -> Generator[None]:
    """Mock updates by incrementing `data_timestamp`."""

    def _mock(self: BaseFile[Any], update_at: datetime | None = None) -> None:
        if not self.is_outdated(update_at):
            return
        record = self._existing_database_record
        if record is None:
            return
        logger.debug(f"Mock Updating {record.key}")
        record.data_timestamp += timedelta(minutes=1)

    with patch.object(BaseFile, "download_if_outdated", _mock):
        yield


@contextmanager
def track_downloads() -> Generator[list[str]]:
    """Track which files are actually downloaded during an operation.

    Yields a list of files that were downloaded.
    """
    downloaded: list[str] = []
    original_download_if_outdated = BaseFile[Any].download_if_outdated

    def _track_downloads(
        self: BaseFile[Any],
        update_at: datetime | None = None,
    ) -> None:
        was_outdated = self.is_outdated(update_at)
        original_download_if_outdated(self, update_at)
        if was_outdated:
            downloaded.append(self.database_record.key)

    with patch.object(BaseFile, "download_if_outdated", _track_downloads):
        yield downloaded
