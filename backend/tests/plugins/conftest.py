# TODO: Validate
"""Configure tests for `Plugin`s."""

import os
from collections.abc import Generator

import pytest

from tests.plugins.plugin_validator.stored_files import (
    check_episodes_before_grouped_download,
    serve_downloads_from_disk,
)

# Plugin tests should not be run on GitHub Actions because there are no cached
# files to use.
# TODO: Load the cached files for the test without having them be in the public repo.
collect_ignore_glob = ["test_*.py"] if "GITHUB_ACTIONS" in os.environ else []


# TODO: Validate
@pytest.fixture(scope="session", autouse=True)
def _stored_downloads() -> Generator[list[str]]:
    with (
        check_episodes_before_grouped_download(),
        serve_downloads_from_disk() as downloaded,
    ):
        yield downloaded
