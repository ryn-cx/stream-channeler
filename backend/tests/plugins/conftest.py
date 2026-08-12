# TODO: Validate
import os

from tests.old_mess.plugins.conftest import _stored_downloads

collect_ignore_glob = ["test_*.py"] if "GITHUB_ACTIONS" in os.environ else []

__all__ = ["_stored_downloads"]
