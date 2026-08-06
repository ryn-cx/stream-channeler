# TODO: Validate
"""Fixtures shared by every app test."""

from typing import Any

import pytest

from plugins.utils.base_plugin.files import BaseFile


@pytest.fixture(autouse=True)
def _block_file_downloads(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stop routes that merge TMDB data from downloading files.

    App tests only exercise the API, so a download is always an unwanted network
    call that `pytest-socket` turns into a failure.
    """

    def _no_download(*_args: Any, **_kwargs: Any) -> None:  # noqa: ANN401
        return

    monkeypatch.setattr(BaseFile, "download_if_outdated", _no_download)
