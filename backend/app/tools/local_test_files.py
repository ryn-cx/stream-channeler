# TODO: Validate
from collections.abc import Generator
from contextlib import contextmanager
from datetime import datetime
from typing import Any
from unittest.mock import patch

from loguru import logger

from app.config import settings
from plugins.utils.base_plugin import BaseFile


# TODO: Validate
@contextmanager
def serve_downloads_from_test_files() -> Generator[None]:
    if settings.ENVIRONMENT != "local":
        yield
        return

    from tests.plugins.plugin_validator_v2.stored_files import (  # noqa: PLC0415 - Only reached on a local run, where the tests are on disk.
        _exists,
        _owner_key,
        restore_stored_metadata,
        stored_file_path,
    )

    original_download_if_outdated = BaseFile[Any].download_if_outdated

    # TODO: Validate
    def _download_if_outdated(
        self: BaseFile[Any],
        update_at: datetime | None = None,
    ) -> None:
        if not self.is_outdated(update_at):
            return

        path = stored_file_path(self)
        if not _exists(path):
            original_download_if_outdated(self, update_at)
            return

        logger.debug(f"Serving {self.file_key()} from {path}")
        self.write(path.read_text(encoding="utf-8") or None)
        restore_stored_metadata(self.database_record, _owner_key(self), path)

    with patch.object(BaseFile, "download_if_outdated", _download_if_outdated):
        yield
