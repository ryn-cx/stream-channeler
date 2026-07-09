from pathlib import Path

APP_PATH = Path(__file__).parent
BACKEND_PATH = APP_PATH.parent
# The maximum number of entries in a single page. If a table has at least this many
# records, pagination/filtering/sorting is done server side, if it has less than this
# many, it is done client side.
MAX_PAGE_SIZE = 10_000
