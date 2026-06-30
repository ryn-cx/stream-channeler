"""Configure tests for `Plugin`s."""

import os

# Plugin tests should not be run on GitHub Actions because there are no cached
# files to use.
# TODO: Load the cached files for the test without having them be in the public repo.
collect_ignore_glob = ["test_*.py"] if "GITHUB_ACTIONS" in os.environ else []
