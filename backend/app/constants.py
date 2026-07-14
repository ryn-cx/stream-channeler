from pathlib import Path

APP_PATH = Path(__file__).parent
BACKEND_PATH = APP_PATH.parent
APP_FOLDER = Path(__file__).parent
BACKEND_FOLDER = APP_FOLDER.parent
PROJECT_FOLDER = BACKEND_FOLDER.parent
TEST_FILES_FOLDER = PROJECT_FOLDER.parent / "stream-channeler-test-files"

# This needs to manually be kept in sync with the value in the frontend.
SERVER_SIDE_THRESHOLD_MAXIMUM = 100_000
DEFAULT_SERVER_SIDE_THRESHOLD = 1_000

# Simple sanity check in case this file ever gets moved to a different location.
if APP_PATH.name != "app":
    msg = "APP_PATH is invalid"
    raise ValueError(msg)
