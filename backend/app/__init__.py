"""Stream Channeler."""

import sys
from pathlib import Path

# TODO: This is a terrible awful fix for a stupid issue
_APP_DIRECTORY = str(Path(__file__).parent)
if sys.path and sys.path[0] == _APP_DIRECTORY:
    sys.path.pop(0)
