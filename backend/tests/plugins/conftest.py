"""Plugin tests replay recorded fixture data and must never hit the network.

They are not collected on CI (GITHUB_ACTIONS), where the recorded data and
credentials are unavailable, so a cache miss would otherwise trigger a download.
collect_ignore_glob is scoped to this directory, so it only affects plugin tests.
"""

import os

collect_ignore_glob = ["test_*.py"] if "GITHUB_ACTIONS" in os.environ else []
