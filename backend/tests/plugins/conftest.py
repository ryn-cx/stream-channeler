"""Plugin tests replay recorded fixture data and must never hit the network.

They are skipped entirely on CI (GITHUB_ACTIONS), where the recorded data and
credentials are unavailable, so a cache miss would otherwise trigger a download.
"""

import os
from pathlib import Path

import pytest

_PLUGIN_TESTS_DIR = Path(__file__).parent


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    if "GITHUB_ACTIONS" not in os.environ:
        return

    skip_on_ci = pytest.mark.skip(
        reason="Plugin tests require recorded data and must not download on CI.",
    )
    for item in items:
        if _PLUGIN_TESTS_DIR in item.path.parents:
            item.add_marker(skip_on_ci)
