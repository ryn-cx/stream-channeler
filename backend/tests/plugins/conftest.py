"""Stop the CI from testing plugins because they require downloaded files."""

import os

collect_ignore_glob = ["test_*.py"] if "GITHUB_ACTIONS" in os.environ else []
