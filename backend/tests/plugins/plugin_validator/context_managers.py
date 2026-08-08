# TODO: Validate
"""Context managers for PluginValidator."""

from collections.abc import Generator
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from unittest.mock import patch

from loguru import logger

from app.constants import ALL_TEST_FILES_FOLDER
from plugins.utils.base_plugin import BaseFile


def _owner_key(file: BaseFile[Any]) -> str:
    """Return the plugin a file class belongs to.

    Read off where the class is declared rather than off the plugin the file is
    being downloaded for, because a plugin downloads files belonging to another
    one (TMDB's, to fill in what its own website leaves out) and both have to
    reach the same stored copy.
    """
    return type(file).__module__.split(".")[1]


def stored_file_path(file: BaseFile[Any]) -> Path:
    """Return where `file` is kept among the stored test files.

    Every file lives in one flat folder under a name built from the plugin that
    owns it and the file's own key, so the same file is stored once no matter
    how many tests reach for it. The separators a key carries are folded into
    the name because a name is all a flat folder has, and `:` is dropped because
    NTFS has no room for it.
    """
    name = f"{_owner_key(file)}/{file.file_key()}".replace(":", " - ")
    return ALL_TEST_FILES_FOLDER / name.replace("/", "__")


@contextmanager
def serve_downloads_from_disk() -> Generator[list[str]]:
    """Serve every download from the stored test files, downloading what is missing.

    A file that has been stored is written straight from disk, so a test runs
    without reaching the network. A file that has not been stored yet is
    downloaded for real and then stored, which is how a test records what it
    needs the first time it is run.

    Yields the keys of the files that had to be downloaded, which is empty on
    every run after the first.
    """
    downloaded: list[str] = []
    original_download = BaseFile[Any]._download  # noqa: SLF001 - Mocked below.

    def _download(self: BaseFile[Any]) -> None:
        path = stored_file_path(self)
        if path.exists():
            logger.debug(f"Serving {self.file_key()} from {path.name}")
            self.write(path.read_text(encoding="utf-8") or None)
            return

        original_download(self)
        downloaded.append(self.file_key())
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.database_record.content or "", encoding="utf-8")
        # Logged as it is stored rather than counted up once the test is over,
        # so a run that fails part way through still says what it downloaded.
        logger.info(f"Stored {self.file_key()} as {path.name}")

    with patch.object(BaseFile, "_download", _download):
        yield downloaded


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
