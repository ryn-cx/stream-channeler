# TODO: Validate
"""Configure tests for `Plugin`s."""

import os
from collections.abc import Generator

import pytest

from tests.plugins.plugin_validator.context_managers import serve_downloads_from_disk

# Plugin tests should not be run on GitHub Actions because there are no cached
# files to use.
# TODO: Load the cached files for the test without having them be in the public repo.
collect_ignore_glob = ["test_*.py"] if "GITHUB_ACTIONS" in os.environ else []


@pytest.fixture(autouse=True)
def _stored_downloads() -> Generator[list[str]]:
    """Answer every download out of the stored test files.

    A plugin downloads whatever it reaches for, and each download is served from
    the file stored for it, so a test runs against real data without reaching
    the network. A file that has not been stored yet is downloaded for real,
    which only the test that records the data is allowed to do.
    """
    with serve_downloads_from_disk() as downloaded:
        yield downloaded
