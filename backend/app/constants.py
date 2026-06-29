# TODO: Validate
from pathlib import Path

APP_PATH = Path(__file__).parent
BACKEND_PATH = APP_PATH.parent
APP_FOLDER = Path(__file__).parent
BACKEND_FOLDER = APP_FOLDER.parent
PROJECT_FOLDER = BACKEND_FOLDER.parent
TEST_FILES_FOLDER = PROJECT_FOLDER.parent / "stream-channeler-test-files"

# This needs to stay in sync with the value in the frontend.
SERVER_SIDE_THRESHOLD_MAXIMUM = 100_000
SERVER_SIDE_THRESHOLD_DEFAULT = 100

# Simple sanity check in case this file ever gets moved to a different location.
if APP_PATH.name != "app":
    msg = "APP_PATH is invalid"
    raise ValueError(msg)
