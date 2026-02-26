from pathlib import Path

APP_PATH = Path(__file__).parent
BACKEND_PATH = APP_PATH.parent
APP_FOLDER = Path(__file__).parent
BACKEND_FOLDER = APP_FOLDER.parent
PROJECT_FOLDER = BACKEND_FOLDER.parent
TEST_FILES_FOLDER = PROJECT_FOLDER.parent / "stream-channeler-test-files"

# Tanstack says it can support 100,000 entries, so that was chosen as the maximum number
# of entries per page.
# https://tanstack.com/table/v8/docs/guide/pagination#should-you-use-client-side-pagination
MAX_ENTRIES_PER_PAGE = 100_000

# Simple sanity check in case this file ever gets moved to a different location.
if APP_PATH.name != "app":
    msg = "APP_PATH is invalid"
    raise ValueError(msg)
